"""
SQLite persistence layer for processed dimuon events and analysis results.

Stores:
  - events table    : one row per processed dimuon event with kinematics
                      and quality flags; indexed for fast REST queries
  - histograms table: serialised HistogramData objects (mass spectrum,
                      Z peak histogram)
  - analysis_runs   : metadata for each pipeline run (timestamp, config,
                      cut summary, Z peak fit)

Design notes
------------
SQLite is used because:
  - Zero-config: no server process required
  - The dataset (~100k events) fits easily in a single file (<50 MB)
  - The processed .db file is committed to the repo so the backend can
    serve it on Railway without re-running the pipeline at deploy time
  - Indexed columns enable sub-100ms REST queries on paginated requests

Schema
------
events:
    id              INTEGER PRIMARY KEY
    run             INTEGER
    event           INTEGER
    invariant_mass  REAL    (GeV)
    pt1, pt2        REAL    (GeV/c)
    eta1, eta2      REAL
    phi1, phi2      REAL    (rad)
    px1,py1,pz1     REAL    (GeV/c)
    px2,py2,pz2     REAL    (GeV/c)
    e1, e2          REAL    (GeV)
    q1, q2          INTEGER (+1 or −1)
    type1, type2    TEXT    ('G', 'T', 'S')
    delta_r         REAL
    z_candidate     INTEGER (0 or 1)
    opp_sign        INTEGER (0 or 1)
    run_id          INTEGER → analysis_runs.id

histograms:
    id              INTEGER PRIMARY KEY
    run_id          INTEGER → analysis_runs.id
    name            TEXT    ('mass_spectrum' | 'z_peak')
    data_json       TEXT    (serialised HistogramData.as_dict())

analysis_runs:
    id              INTEGER PRIMARY KEY
    timestamp       TEXT    (ISO-8601)
    dataset         TEXT
    config_json     TEXT
    cut_summary_json TEXT
    z_peak_fit_json TEXT
    n_events        INTEGER
    n_z_candidates  INTEGER
"""

from __future__ import annotations

import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator, Iterator

import pandas as pd

from pipeline.analysis import AnalysisResult, HistogramData

logger = logging.getLogger(__name__)

class DimuonStore:
    """
    Manages all SQLite I/O for the LHC Stream Platform.

    Usage
    -----
    store = DimuonStore("data/processed/events.db")
    run_id = store.save_analysis(result, dataset_name="dimuon_run2010b")
    df = store.query_events(z_candidate=True, limit=100)
    hist = store.get_histogram(run_id, "mass_spectrum")
    """

    SCHEMA = """
    CREATE TABLE IF NOT EXISTS analysis_runs (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp        TEXT    NOT NULL,
        dataset          TEXT    NOT NULL,
        config_json      TEXT,
        cut_summary_json TEXT,
        z_peak_fit_json  TEXT,
        n_events         INTEGER,
        n_z_candidates   INTEGER
    );

    CREATE TABLE IF NOT EXISTS events (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        run             INTEGER NOT NULL,
        event           INTEGER NOT NULL,
        invariant_mass  REAL    NOT NULL,
        pt1             REAL,
        pt2             REAL,
        eta1            REAL,
        eta2            REAL,
        phi1            REAL,
        phi2            REAL,
        px1             REAL,
        py1             REAL,
        pz1             REAL,
        px2             REAL,
        py2             REAL,
        pz2             REAL,
        e1              REAL,
        e2              REAL,
        q1              INTEGER,
        q2              INTEGER,
        type1           TEXT,
        type2           TEXT,
        delta_r         REAL,
        z_candidate     INTEGER NOT NULL DEFAULT 0,
        opp_sign        INTEGER NOT NULL DEFAULT 0,
        run_id          INTEGER NOT NULL,
        FOREIGN KEY (run_id) REFERENCES analysis_runs(id)
    );

    CREATE TABLE IF NOT EXISTS histograms (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id      INTEGER NOT NULL,
        name        TEXT    NOT NULL,
        data_json   TEXT    NOT NULL,
        FOREIGN KEY (run_id) REFERENCES analysis_runs(id)
    );

    CREATE INDEX IF NOT EXISTS idx_events_mass       ON events (invariant_mass);
    CREATE INDEX IF NOT EXISTS idx_events_z          ON events (z_candidate);
    CREATE INDEX IF NOT EXISTS idx_events_pt1        ON events (pt1);
    CREATE INDEX IF NOT EXISTS idx_events_run_id     ON events (run_id);
    CREATE INDEX IF NOT EXISTS idx_histograms_run    ON histograms (run_id, name);
    """

    def __init__(self, db_path: str | Path = "data/processed/events.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def _connect(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")   # better concurrent read
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._connect() as conn:
            for statement in self.SCHEMA.strip().split(";"):
                stmt = statement.strip()
                if stmt:
                    conn.execute(stmt)
        logger.info("Database ready: %s", self.db_path)

    def save_analysis(
        self,
        result: AnalysisResult,
        dataset_name: str,
        recreate: bool = False,
    ) -> int:
        """
        Persist a full AnalysisResult to SQLite.
        """
        if recreate:
            self._drop_data_tables()
            self._init_schema()

        cs = result.cut_summary

        with self._connect() as conn:
            # 1. Insert analysis run metadata
            cur = conn.execute(
                """
                INSERT INTO analysis_runs
                    (timestamp, dataset, config_json, cut_summary_json,
                     z_peak_fit_json, n_events, n_z_candidates)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    datetime.now(timezone.utc).isoformat(),
                    dataset_name,
                    json.dumps(result.config_used),
                    json.dumps(cs.as_dict()),
                    json.dumps(result.z_peak_fit.as_dict()) if result.z_peak_fit else None,
                    cs.total_input,
                    cs.after_z_window,
                ),
            )
            run_id: int = cur.lastrowid
            logger.info("Created analysis run id=%d", run_id)

            # 2. Insert events in bulk
            df = result.processed_df
            rows = self._df_to_rows(df, run_id)
            conn.executemany(
                """
                INSERT INTO events
                    (run, event, invariant_mass,
                     pt1, pt2, eta1, eta2, phi1, phi2,
                     px1, py1, pz1, px2, py2, pz2,
                     e1, e2, q1, q2, type1, type2,
                     delta_r, z_candidate, opp_sign, run_id)
                VALUES
                    (:run, :event, :invariant_mass,
                     :pt1, :pt2, :eta1, :eta2, :phi1, :phi2,
                     :px1, :py1, :pz1, :px2, :py2, :pz2,
                     :e1, :e2, :q1, :q2, :type1, :type2,
                     :delta_r, :z_candidate, :opp_sign, :run_id)
                """,
                rows,
            )
            logger.info("Inserted %d events", len(rows))

            # 3. Insert histograms
            for name, hist in [
                ("mass_spectrum", result.mass_histogram),
                ("z_peak", result.z_peak_histogram),
            ]:
                conn.execute(
                    "INSERT INTO histograms (run_id, name, data_json) VALUES (?, ?, ?)",
                    (run_id, name, json.dumps(hist.as_dict())),
                )
            logger.info("Saved 2 histograms for run_id=%d", run_id)

        return run_id

    def query_events(
        self,
        z_candidate: bool | None = None,
        mass_min: float | None = None,
        mass_max: float | None = None,
        pt_min: float | None = None,
        run_id: int | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> pd.DataFrame:
        """
        Query events with optional filters.
        """
        conditions = []
        params: list = []

        if run_id is not None:
            conditions.append("run_id = ?")
            params.append(run_id)
        else:
            # Use latest run by default
            conditions.append("run_id = (SELECT MAX(id) FROM analysis_runs)")

        if z_candidate is not None:
            conditions.append("z_candidate = ?")
            params.append(1 if z_candidate else 0)

        if mass_min is not None:
            conditions.append("invariant_mass >= ?")
            params.append(mass_min)

        if mass_max is not None:
            conditions.append("invariant_mass <= ?")
            params.append(mass_max)

        if pt_min is not None:
            conditions.append("pt1 >= ? AND pt2 >= ?")
            params.extend([pt_min, pt_min])

        where = " AND ".join(conditions) if conditions else "1"
        query = f"""
            SELECT * FROM events
            WHERE {where}
            ORDER BY invariant_mass DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])

        with self._connect() as conn:
            df = pd.read_sql_query(query, conn, params=params)

        return df

    def get_histogram(
        self,
        name: str = "mass_spectrum",
        run_id: int | None = None,
    ) -> dict | None:
        """
        Retrieve a histogram by name for a given run (latest if run_id is None).

        Returns the HistogramData.as_dict() dict, or None if not found.
        """
        with self._connect() as conn:
            if run_id is None:
                row = conn.execute(
                    """
                    SELECT data_json FROM histograms
                    WHERE name = ?
                      AND run_id = (SELECT MAX(id) FROM analysis_runs)
                    """,
                    (name,),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT data_json FROM histograms WHERE run_id = ? AND name = ?",
                    (run_id, name),
                ).fetchone()

        if row is None:
            return None
        return json.loads(row["data_json"])

    def get_latest_run(self, dataset_id: int | None = None) -> dict | None:
        """Return metadata for the most recent analysis run, optionally filtered by dataset ID."""
        query = "SELECT * FROM analysis_runs"
        params = []
        if dataset_id is not None:
            # Se passi l'ID del run, la colonna nella tabella 'analysis_runs' probabilmente è 'id'
            query += " WHERE id = ?"
            params.append(dataset_id)
        query += " ORDER BY id DESC LIMIT 1"

        with self._connect() as conn:
            row = conn.execute(query, params).fetchone()
        if row is None:
            return None
        d = dict(row)
        for key in ("config_json", "cut_summary_json", "z_peak_fit_json"):
            if d.get(key):
                d[key] = json.loads(d[key])
        return d

    def get_stats(self, dataset_id: int | None = None) -> dict:
        """Return aggregate statistics for a specific dataset run."""
        subquery = "SELECT MAX(id) FROM analysis_runs"
        params = []
        if dataset_id is not None:
            # Anche qui cerchiamo il run per 'id'
            subquery += " WHERE id = ?"
            params.append(dataset_id)

        query = f"""
            SELECT
                COUNT(*)                            AS total,
                SUM(z_candidate)                    AS z_total,
                AVG(invariant_mass)                 AS mass_mean,
                MIN(invariant_mass)                 AS mass_min,
                MAX(invariant_mass)                 AS mass_max,
                AVG(CASE WHEN z_candidate=1
                         THEN invariant_mass END)   AS z_mass_mean,
                AVG(pt1)                            AS pt1_mean,
                AVG(pt2)                            AS pt2_mean
            FROM events
            WHERE run_id = ({subquery})
        """

        with self._connect() as conn:
            row = conn.execute(query, params).fetchone()

        if row is None or row["total"] == 0:
            return {}

        return {
            "total_events": row["total"],
            "z_candidates": row["z_total"],
            "mass_mean_gev": round(row["mass_mean"] or 0, 3),
            "mass_min_gev": round(row["mass_min"] or 0, 3),
            "mass_max_gev": round(row["mass_max"] or 0, 3),
            "z_mass_mean_gev": round(row["z_mass_mean"] or 0, 3),
            "pt1_mean_gev": round(row["pt1_mean"] or 0, 3),
            "pt2_mean_gev": round(row["pt2_mean"] or 0, 3),
        }

    def _drop_data_tables(self) -> None:
        with self._connect() as conn:
            conn.execute("DROP TABLE IF EXISTS histograms")
            conn.execute("DROP TABLE IF EXISTS events")
            conn.execute("DROP TABLE IF EXISTS analysis_runs")
        logger.info("Dropped existing data tables")

    @staticmethod
    def _df_to_rows(df: pd.DataFrame, run_id: int) -> list[dict]:
        """Convert DataFrame to list of dicts for executemany insert."""
        rows = []
        for _, r in df.iterrows():
            rows.append({
                "run": int(r["Run"]),
                "event": int(r["Event"]),
                "invariant_mass": float(r["M"]),
                "pt1": float(r["pt1"]),
                "pt2": float(r["pt2"]),
                "eta1": float(r["eta1"]),
                "eta2": float(r["eta2"]),
                "phi1": float(r["phi1"]),
                "phi2": float(r["phi2"]),
                "px1": float(r["px1"]),
                "py1": float(r["py1"]),
                "pz1": float(r["pz1"]),
                "px2": float(r["px2"]),
                "py2": float(r["py2"]),
                "pz2": float(r["pz2"]),
                "e1": float(r["E1"]),
                "e2": float(r["E2"]),
                "q1": int(r["Q1"]),
                "q2": int(r["Q2"]),
                "type1": str(r["Type1"]).strip(),
                "type2": str(r["Type2"]).strip(),
                "delta_r": float(r.get("delta_r", 0.0)),
                "z_candidate": int(bool(r.get("z_candidate", False))),
                "opp_sign": int(bool(r.get("opp_sign", False))),
                "run_id": run_id,
            })
        return rows