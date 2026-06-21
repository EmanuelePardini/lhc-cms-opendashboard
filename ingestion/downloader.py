"""
Downloads CMS dimuon CSV datasets from the CERN Open Data Portal.

Dataset used:
    McCauley, Thomas (2014). Dimuon event information derived from the
    Run2010B public Mu dataset. CERN Open Data Portal.
    DOI: 10.7483/OPENDATA.CMS.CB8H.MFFA
    URL: https://opendata.cern.ch/record/700

    The dataset contains 100k dimuon events selected from the CMS Mu primary
    dataset (Run2010B). Each row is one event with two muon candidates whose
    invariant mass lies in the range 2–110 GeV. At least one muon is required
    to be a high-quality "global" muon (track reconstructed in both the inner
    tracker and muon chambers).

CSV columns (record 700 / 545 format):
    Run, Event,
    Type1, E1, px1, py1, pz1, pt1, eta1, phi1, Q1,
    Type2, E2, px2, py2, pz2, pt2, eta2, phi2, Q2,
    M
    where:
        Type  = muon reconstruction type ('G' = global, 'T' = tracker-only,
                'S' = standalone muon)
        E     = energy [GeV]
        px/py/pz = Cartesian momentum components [GeV/c]
        pt    = transverse momentum [GeV/c]
        eta   = pseudorapidity (η = −ln tan(θ/2))
        phi   = azimuthal angle [rad]
        Q     = electric charge (+1 or −1)
        M     = precomputed invariant mass [GeV/c²]

References:
    [1] CERN Open Data Portal — record 700
        https://opendata.cern.ch/record/700
    [2] CERN Open Data Portal — record 545 (Run2011A, larger statistics)
        https://opendata.cern.ch/record/545
    [3] Quick start to CMS Open Data — Physics
        https://opendata-education.github.io/en_Physics/
"""

import hashlib
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

import requests

logger = logging.getLogger(__name__)


@dataclass
class DatasetInfo:
    """Metadata for a CERN Open Data CSV dataset."""
    record_id: str
    name: str
    url: str
    doi: str
    n_events_approx: int
    description: str
    # optional SHA-256 hex digest for integrity check (None = skip check)
    sha256: str = None


DATASETS: dict[str, DatasetInfo] = {
    # 100k events, Run2010B — lightweight, ideal for development
    "dimuon_run2010b": DatasetInfo(
        record_id="700",
        name="dimuon_run2010b",
        url="https://opendata.cern.ch/record/700/files/MuRun2010B.csv",
        doi="10.7483/OPENDATA.CMS.CB8H.MFFA",
        n_events_approx=100_000,
        description=(
            "100k dimuon events from CMS Run2010B. Two-muon events with "
            "invariant mass 2–110 GeV, at least one global muon."
        ),
        sha256=None,  # set if known
    ),
    # ~986k events, Run2011A — full statistics for Z peak analysis
    "dimuon_run2011a": DatasetInfo(
        record_id="545",
        name="dimuon_run2011a",
        url="https://opendata.cern.ch/record/545/files/Dimuon_DoubleMu.csv",
        doi="10.7483/OPENDATA.CMS.IYVQ.1J0G",
        n_events_approx=986_100,
        description=(
            "~986k dimuon events from CMS Run2011A (DoubleMu stream). "
            "Covers invariant mass 0.3–300 GeV. Optimal for Z boson peak."
        ),
        sha256=None,
    ),
}

DEFAULT_DATASET = "dimuon_run2011a"


class CERNOpenDataDownloader:
    """
    Downloads CMS dimuon CSV files from the CERN Open Data Portal with
    resumable download support, SHA-256 integrity check, and local caching.
    """

    CHUNK_SIZE = 1024 * 256  # 256 KB per chunk

    def __init__(self, cache_dir: Path = "data/cache") -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get(self, dataset_name: str = DEFAULT_DATASET) -> Path:
        """
        Return the local path to the dataset CSV, downloading if necessary.
        """
        if dataset_name not in DATASETS:
            available = list(DATASETS.keys())
            raise KeyError(
                f"Unknown dataset '{dataset_name}'. Available: {available}"
            )

        info = DATASETS[dataset_name]
        dest = self.cache_dir / f"{info.name}.csv"

        if dest.exists():
            logger.info(
                "Cache hit: %s (%s bytes)",
                dest.name,
                f"{dest.stat().st_size:,}",
            )
            if info.sha256:
                self._verify_sha256(dest, info.sha256)
            return dest

        logger.info(
            "Downloading dataset '%s' from CERN Open Data Portal …", dataset_name
        )
        logger.info("  DOI  : %s", info.doi)
        logger.info("  URL  : %s", info.url)
        logger.info("  ~%s events expected", f"{info.n_events_approx:,}")

        self._download(info.url, dest)

        if info.sha256:
            self._verify_sha256(dest, info.sha256)

        size_mb = dest.stat().st_size / 1024 / 1024
        logger.info("Download complete: %.1f MB → %s", size_mb, dest)

        return dest

    def list_datasets(self) -> list[dict]:
        """Return metadata for all registered datasets."""
        return [
            {
                "name": info.name,
                "record_id": info.record_id,
                "doi": info.doi,
                "n_events_approx": info.n_events_approx,
                "cached": (self.cache_dir / f"{info.name}.csv").exists(),
                "description": info.description,
            }
            for info in DATASETS.values()
        ]

    def purge_cache(self, dataset_name: str = None) -> None:
        """Delete cached files. Pass None to purge all."""
        if dataset_name:
            target = self.cache_dir / f"{DATASETS[dataset_name].name}.csv"
            if target.exists():
                target.unlink()
                logger.info("Purged: %s", target)
        else:
            for f in self.cache_dir.glob("*.csv"):
                f.unlink()
                logger.info("Purged: %s", f)

    def _download(self, url: str, dest: Path) -> None:
        """Stream-download url to dest with a .part temporary file."""
        part = dest.with_suffix(".part")

        # Resume if partial download exists
        downloaded = part.stat().st_size if part.exists() else 0
        headers = {"Range": f"bytes={downloaded}-"} if downloaded > 0 else {}

        if downloaded:
            logger.info("Resuming from byte %s", f"{downloaded:,}")

        response = requests.get(url, stream=True, headers=headers, timeout=30)

        # 416 = range not satisfiable → server doesn't support resume,
        # start fresh
        if response.status_code == 416:
            logger.warning("Server does not support resume; restarting.")
            part.unlink(missing_ok=True)
            downloaded = 0
            response = requests.get(url, stream=True, timeout=30)

        response.raise_for_status()

        total = int(response.headers.get("Content-Length", 0)) + downloaded
        mode = "ab" if downloaded else "wb"

        with open(part, mode) as fh:
            for chunk in response.iter_content(chunk_size=self.CHUNK_SIZE):
                if chunk:
                    fh.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        pct = downloaded / total * 100
                        logger.debug("  %.1f%%  (%s / %s bytes)", pct,
                                     f"{downloaded:,}", f"{total:,}")

        part.rename(dest)

    @staticmethod
    def _verify_sha256(path: Path, expected: str) -> None:
        """Raise ValueError if the file's SHA-256 digest doesn't match."""
        logger.info("Verifying SHA-256 …")
        sha = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                sha.update(chunk)
        actual = sha.hexdigest()
        if actual != expected:
            raise ValueError(
                f"SHA-256 mismatch for {path.name}.\n"
                f"  Expected : {expected}\n"
                f"  Got      : {actual}"
            )
        logger.info("SHA-256 OK")