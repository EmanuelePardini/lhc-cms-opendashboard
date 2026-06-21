"""
Parses CMS dimuon CSV files into structured DimuonEvent objects and
pandas DataFrames ready for the analysis pipeline.

Physics background
------------------
Each row in the CSV represents one proton-proton collision event in which
exactly two muons were reconstructed. The parser validates the data and
computes derived kinematic quantities.

Invariant mass
~~~~~~~~~~~~~~
The invariant mass of the dimuon system is defined by the relativistic
energy-momentum relation:

    M² = (E₁ + E₂)² − |p₁ + p₂|²
       = (E₁ + E₂)² − (px₁+px₂)² − (py₁+py₂)² − (pz₁+pz₂)²

where energies and momenta are in GeV (natural units, c=1).
The dataset already provides M precomputed, but we re-derive it from
four-momenta for validation and to expose the formula explicitly.

Pseudorapidity
~~~~~~~~~~~~~~
η = −ln tan(θ/2)

where θ is the polar angle from the beam axis. η ≈ 0 is perpendicular to
the beam; |η| → ∞ is along the beam direction. CMS muon acceptance is
|η| < 2.4. Useful because Lorentz boosts along the beam axis shift η by
a constant — so distributions in η are approximately boost-invariant.

Transverse momentum
~~~~~~~~~~~~~~~~~~~
pT = √(px² + py²)

Only the component transverse to the beam can be accurately measured
(beam particles have unknown longitudinal momentum), so pT is the primary
kinematic variable for event selection.

Azimuthal angle
~~~~~~~~~~~~~~~
φ = atan2(py, px) ∈ [−π, π]

ΔR separation
~~~~~~~~~~~~~
ΔR = √(Δη² + Δφ²)
Used to measure angular separation between particles in the detector.

Muon reconstruction types (Type column)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    G = Global muon  — track reconstructed in inner tracker + muon chambers
                       (highest quality, used for Z/W/Higgs analyses)
    T = Tracker-only — reconstructed in inner tracker only
    S = Standalone   — reconstructed in muon chambers only

References
----------
[1] CMS Collaboration — Physics Objects documentation
    https://opendata.cern.ch/docs/cms-physics-objects-2011
[2] Particle Data Group — Review of Particle Physics (2022)
    https://pdg.lbl.gov
[3] Griffiths, D. — Introduction to Elementary Particles, 2nd ed.
    Wiley-VCH (2008) — Chapter 9: kinematics
[4] McCauley, T. (2014) — Dimuon event information derived from Run2010B
    CERN Open Data Portal. DOI:10.7483/OPENDATA.CMS.CB8H.MFFA
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

MUON_MASS_GEV: float = 0.10566   # GeV/c²  (PDG 2022)
Z_BOSON_MASS_GEV: float = 91.188  # GeV/c²  (PDG 2022)
Z_BOSON_WIDTH_GEV: float = 2.495  # GeV     (PDG 2022)

# Standard CMS acceptance window for muons
ETA_MAX: float = 2.4
PT_MIN_GEV: float = 3.0           # loose minimum for this dataset

# Z-window for tagging Z boson candidate events
Z_WINDOW_LOW_GEV: float = 76.0
Z_WINDOW_HIGH_GEV: float = 106.0

# Expected CSV columns in order (record 700 / 545 format)
EXPECTED_COLUMNS: list[str] = [
    "Run", "Event",
    "Type1", "E1", "px1", "py1", "pz1", "pt1", "eta1", "phi1", "Q1",
    "Type2", "E2", "px2", "py2", "pz2", "pt2", "eta2", "phi2", "Q2",
    "M",
]


@dataclass
class Muon:
    """
    Kinematic and quality information for a single reconstructed muon.

    All momenta in GeV/c, energy in GeV, angles in radians (φ) or
    dimensionless (η).
    """
    muon_type: str      # 'G', 'T', or 'S'
    energy: float       # E  [GeV]
    px: float           # px [GeV/c]
    py: float           # py [GeV/c]
    pz: float           # pz [GeV/c]
    pt: float           # pT [GeV/c]
    eta: float          # pseudorapidity
    phi: float          # azimuthal angle [rad]
    charge: int         # electric charge (+1 or −1)

    @property
    def p(self) -> float:
        """Total 3-momentum magnitude |p| [GeV/c]."""
        return math.sqrt(self.px**2 + self.py**2 + self.pz**2)

    @property
    def is_global(self) -> bool:
        """True if muon was reconstructed as a global muon (Type='G')."""
        return self.muon_type == "G"

    def track_points(self, n_points: int = 20) -> list[dict[str, float]]:
        """
        Generate a simplified helical track as a list of 3-D points for
        Three.js rendering.

        The track is approximated as a straight line from the interaction
        point (0,0,0) in the direction of the muon momentum. A real CMS
        track would include curvature from the 3.8 T solenoid field, but
        for visualisation purposes a line is sufficient.
        """
        # CMS inner detector radius ≈ 1.1 m, forward ≈ 3 m
        # We scale the direction vector to detector dimensions
        scale = 1.1 / (self.pt + 1e-9)   # crude radial scaling
        dx = self.px * scale
        dy = self.py * scale
        dz = self.pz * scale * 0.3        # compress z for display

        return [
            {
                "x": round(dx * t / n_points, 4),
                "y": round(dy * t / n_points, 4),
                "z": round(dz * t / n_points, 4),
            }
            for t in range(n_points + 1)
        ]


@dataclass
class DimuonEvent:
    """
    A single dimuon collision event from the CMS detector.

    Contains the two reconstructed muons, derived kinematic quantities,
    and quality flags.
    """
    run: int
    event: int
    muon1: Muon
    muon2: Muon
    invariant_mass: float

    invariant_mass_check: float = field(init=False)
    delta_r: float = field(init=False)
    is_opposite_sign: bool = field(init=False)
    at_least_one_global: bool = field(init=False)
    is_z_candidate: bool = field(init=False)
    passes_acceptance: bool = field(init=False)

    def __post_init__(self) -> None:
        m = self.muon1
        n = self.muon2

        # Use precomputed M from dataset (stored before we overwrite)
        # We also derive it from four-momenta to cross-check.
        e_sum = m.energy + n.energy
        px_sum = m.px + n.px
        py_sum = m.py + n.py
        pz_sum = m.pz + n.pz
        m2 = e_sum**2 - (px_sum**2 + py_sum**2 + pz_sum**2)
        self.invariant_mass_check = math.sqrt(max(m2, 0.0))

        # ΔR angular separation
        d_eta = m.eta - n.eta
        d_phi = m.phi - n.phi
        # Wrap Δφ to [−π, π]
        d_phi = (d_phi + math.pi) % (2 * math.pi) - math.pi
        self.delta_r = math.sqrt(d_eta**2 + d_phi**2)

        # Quality flags
        self.is_opposite_sign = (m.charge * n.charge) == -1
        self.at_least_one_global = m.is_global or n.is_global

        # CMS acceptance: both muons within |η| < 2.4, pT > PT_MIN
        self.passes_acceptance = (
            abs(m.eta) < ETA_MAX and abs(n.eta) < ETA_MAX
            and m.pt > PT_MIN_GEV and n.pt > PT_MIN_GEV
        )

        # Z boson candidate: opposite-sign, global, in mass window
        self.is_z_candidate = (
            self.is_opposite_sign
            and self.at_least_one_global
            and self.passes_acceptance
            and Z_WINDOW_LOW_GEV < self.invariant_mass < Z_WINDOW_HIGH_GEV
        )

    def to_dict(self) -> dict:
        """Serialise to a flat dict suitable for JSON / WebSocket payload."""
        return {
            "run": self.run,
            "event": self.event,
            "invariant_mass": round(self.invariant_mass, 4),
            "delta_r": round(self.delta_r, 4),
            "is_opposite_sign": self.is_opposite_sign,
            "is_z_candidate": self.is_z_candidate,
            "passes_acceptance": self.passes_acceptance,
            "muon1": {
                "type": self.muon1.muon_type,
                "energy": round(self.muon1.energy, 4),
                "px": round(self.muon1.px, 4),
                "py": round(self.muon1.py, 4),
                "pz": round(self.muon1.pz, 4),
                "pt": round(self.muon1.pt, 4),
                "eta": round(self.muon1.eta, 4),
                "phi": round(self.muon1.phi, 4),
                "charge": self.muon1.charge,
                "tracks": self.muon1.track_points(),
            },
            "muon2": {
                "type": self.muon2.muon_type,
                "energy": round(self.muon2.energy, 4),
                "px": round(self.muon2.px, 4),
                "py": round(self.muon2.py, 4),
                "pz": round(self.muon2.pz, 4),
                "pt": round(self.muon2.pt, 4),
                "eta": round(self.muon2.eta, 4),
                "phi": round(self.muon2.phi, 4),
                "charge": self.muon2.charge,
                "tracks": self.muon2.track_points(),
            },
        }


class DimuonCSVParser:
    """
    Parses a CMS dimuon CSV file (CERN Open Data format) into DimuonEvent
    objects and / or a pandas DataFrame.
    """

    def __init__(
        self,
        mass_tolerance: float = 0.05,
        warn_on_mismatch: bool = True,
    ) -> None:

        self.mass_tolerance = mass_tolerance
        self.warn_on_mismatch = warn_on_mismatch

    def to_dataframe(
            self,
            csv_path: str | Path,
            max_rows: int | None = None,
    ) -> pd.DataFrame:
        """
        Parse CSV into a pandas DataFrame with all original columns plus
        derived quantities.

        Additional columns added:
            M_derived   — invariant mass recomputed from four-momenta [GeV]
            delta_r     — ΔR angular separation between the two muons
            opp_sign    — True if Q1 * Q2 == −1
            any_global  — True if Type1 == 'G' or Type2 == 'G'
            in_accept   — True if both muons pass CMS acceptance cuts
            z_candidate — True if event is a Z boson candidate
        """
        path = Path(csv_path)
        logger.info("Reading CSV: %s", path)

        # Read the raw CSV file
        df = pd.read_csv(
            path,
            nrows=max_rows,
        )

        # 1. Clean whitespace and normalize column case
        df.columns = df.columns.str.strip()

        # Map lowercase CSV columns to the expected CamelCase format.
        # This ensures cross-compatibility between Run 2010 (Type1) and Run 2011 (type1).
        column_mapping = {col.lower(): col for col in EXPECTED_COLUMNS}
        df = df.rename(columns=lambda c: column_mapping.get(c.lower(), c))

        # 2. Validation (columns will now have the correct case if they exist)
        self._validate_columns(df)

        # 3. Enforce proper data types after renaming
        type_fix = {
            "Run": int, "Event": int,
            "Type1": str, "Type2": str,
            "Q1": int, "Q2": int,
        }
        # Only convert columns that are actually present to prevent unexpected KeyErrors
        type_fix = {k: v for k, v in type_fix.items() if k in df.columns}
        df = df.astype(type_fix)

        # Strip whitespace from string values (some CERN datasets contain padded spaces)
        df["Type1"] = df["Type1"].str.strip()
        df["Type2"] = df["Type2"].str.strip()

        # Derived: invariant mass from four-momenta (cross-check)
        e_sum = df["E1"] + df["E2"]
        px_sum = df["px1"] + df["px2"]
        py_sum = df["py1"] + df["py2"]
        pz_sum = df["pz1"] + df["pz2"]
        m2 = e_sum ** 2 - (px_sum ** 2 + py_sum ** 2 + pz_sum ** 2)
        df["M_derived"] = np.sqrt(np.maximum(m2, 0.0))

        if self.warn_on_mismatch:
            # Check fractional deviation
            frac_diff = np.abs(df["M_derived"] - df["M"]) / (df["M"] + 1e-9)
            n_bad = (frac_diff > self.mass_tolerance).sum()
            if n_bad > 0:
                logger.warning(
                    "%d rows have |M_derived − M_csv| / M_csv > %.0f%% "
                    "(may indicate floating-point rounding in source data)",
                    n_bad, self.mass_tolerance * 100,
                )

        # Derived: ΔR angular separation
        d_phi = df["phi1"] - df["phi2"]
        d_phi = (d_phi + np.pi) % (2 * np.pi) - np.pi
        df["delta_r"] = np.sqrt((df["eta1"] - df["eta2"]) ** 2 + d_phi ** 2)

        # Quality and selection flags
        df["opp_sign"] = (df["Q1"] * df["Q2"]) == -1
        df["any_global"] = (df["Type1"] == "G") | (df["Type2"] == "G")
        df["in_accept"] = (
                (df["eta1"].abs() < ETA_MAX) & (df["eta2"].abs() < ETA_MAX)
                & (df["pt1"] > PT_MIN_GEV) & (df["pt2"] > PT_MIN_GEV)
        )
        df["z_candidate"] = (
                df["opp_sign"] & df["any_global"] & df["in_accept"]
                & df["M"].between(Z_WINDOW_LOW_GEV, Z_WINDOW_HIGH_GEV)
        )

        n_total = len(df)
        n_opp = df["opp_sign"].sum()
        n_z = df["z_candidate"].sum()
        logger.info(
            "Parsed %s events | opposite-sign: %s (%.1f%%) | "
            "Z candidates: %s (%.1f%%)",
            f"{n_total:,}", f"{n_opp:,}", n_opp / n_total * 100,
            f"{n_z:,}", n_z / n_total * 100,
        )

        return df

    def to_events(
        self,
        csv_path: str | Path,
        max_events: int | None = None,
    ) -> list[DimuonEvent]:
        """
        Parse CSV into a list of DimuonEvent dataclass instances.

        This is lower-throughput than to_dataframe() but produces
        fully-typed objects with 3-D track points.
        """
        df = self.to_dataframe(csv_path, max_rows=max_events)
        events: list[DimuonEvent] = []

        for _, row in df.iterrows():
            m1 = Muon(
                muon_type=row["Type1"],
                energy=row["E1"], px=row["px1"], py=row["py1"], pz=row["pz1"],
                pt=row["pt1"], eta=row["eta1"], phi=row["phi1"],
                charge=int(row["Q1"]),
            )
            m2 = Muon(
                muon_type=row["Type2"],
                energy=row["E2"], px=row["px2"], py=row["py2"], pz=row["pz2"],
                pt=row["pt2"], eta=row["eta2"], phi=row["phi2"],
                charge=int(row["Q2"]),
            )
            ev = DimuonEvent(
                run=int(row["Run"]),
                event=int(row["Event"]),
                muon1=m1,
                muon2=m2,
                invariant_mass=float(row["M"]),
            )
            events.append(ev)

        return events

    def summary(self, df: pd.DataFrame) -> dict:
        """
        Compute a physics summary dict from a parsed DataFrame.
        Useful for the /stats REST endpoint.
        """
        z = df[df["z_candidate"]]
        return {
            "total_events": len(df),
            "opposite_sign_events": int(df["opp_sign"].sum()),
            "z_candidates": int(df["z_candidate"].sum()),
            "mass_mean_gev": round(float(df["M"].mean()), 3),
            "mass_std_gev": round(float(df["M"].std()), 3),
            "mass_z_peak_mean_gev": round(float(z["M"].mean()), 3) if len(z) > 0 else None,
            "pt1_mean_gev": round(float(df["pt1"].mean()), 3),
            "pt2_mean_gev": round(float(df["pt2"].mean()), 3),
            "global_muon_fraction": round(
                float((df["Type1"] == "G").mean() + (df["Type2"] == "G").mean()) / 2, 3
            ),
        }

    def _validate_columns(self, df: pd.DataFrame) -> None:
        missing = [c for c in EXPECTED_COLUMNS if c not in df.columns]
        if missing:
            raise ValueError(
                f"CSV is missing expected columns: {missing}\n"
                f"Found columns: {list(df.columns)}"
            )