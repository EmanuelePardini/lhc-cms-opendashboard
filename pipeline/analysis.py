"""
analysis.py
-----------
Analysis pipeline for CMS dimuon events.

Loads configuration from config/pipeline.yaml, applies kinematic cuts to
a parsed DataFrame, computes histogram data, and produces analysis results
ready for storage and streaming.

Physics implemented
-------------------
1. Kinematic selection cuts
   Applied to select well-reconstructed Z→μμ candidate events.
   Each cut removes a source of background or poorly-measured events.

2. Invariant mass histogram
   Bins events by dimuon invariant mass M. The resulting spectrum shows
   resonance peaks at known particles:
     - J/ψ  ≈ 3.097 GeV  (charmonium)
     - Υ    ≈ 9.46  GeV  (bottomonium family, 3 peaks)
     - Z⁰   ≈ 91.19 GeV  (electroweak neutral gauge boson)

   The Z peak is the primary signal of this analysis. Its position
   and width confirm the dataset quality and the correctness of the
   momentum calibration.

3. Z peak fit (Breit-Wigner approximation)
   A relativistic Breit-Wigner distribution describes the Z lineshape:
     dσ/dM ∝ M² / ((M² − M_Z²)² + M_Z²Γ_Z²)
   where M_Z = 91.188 GeV and Γ_Z = 2.495 GeV (PDG values).
   We fit the peak region (76–106 GeV) to extract the measured M_Z and Γ_Z.

References
----------
[1] PDG 2022 — Z boson properties
    https://pdg.lbl.gov/2022/listings/rpp2022-list-z-boson.pdf
[2] CMS Collaboration (2011) — Measurement of the Z/γ* → μμ cross section
    CMS-EWK-10-005, arXiv:1107.4789
[3] Barlow, R. — Statistics: A Guide to the Use of Statistical Methods
    in the Physical Sciences, Wiley (1989)
[4] CERN Open Data dimuon analysis notebook
    https://opendata.cern.ch/record/12342
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

logger = logging.getLogger(__name__)

Z_MASS_PDG = 91.188    # GeV/c²
Z_WIDTH_PDG = 2.495    # GeV

def load_config(config_path: str | Path = "config/pipeline.yaml") -> dict:
    """Load and return the pipeline YAML configuration."""
    with open(config_path, "r") as fh:
        cfg = yaml.safe_load(fh)
    logger.info("Loaded config from %s", config_path)
    return cfg

@dataclass
class CutSummary:
    """Tracks how many events survive each sequential cut."""
    total_input: int
    after_acceptance: int
    after_opposite_sign: int
    after_global_muon: int
    after_delta_r: int
    after_z_window: int   # = final Z candidates

    @property
    def efficiency(self) -> float:
        """Fraction of input events that are Z candidates."""
        return self.after_z_window / self.total_input if self.total_input else 0.0

    def as_dict(self) -> dict:
        return {
            "total_input": self.total_input,
            "after_acceptance": self.after_acceptance,
            "after_opposite_sign": self.after_opposite_sign,
            "after_global_muon": self.after_global_muon,
            "after_delta_r": self.after_delta_r,
            "z_candidates": self.after_z_window,
            "efficiency_pct": round(self.efficiency * 100, 2),
        }


@dataclass
class HistogramData:
    """A 1-D histogram with bin edges and counts."""
    bin_edges: list[float]    # length n_bins + 1
    counts: list[int]         # length n_bins
    label: str
    x_label: str = "M [GeV]"
    y_label: str = "Events"

    @property
    def bin_centers(self) -> list[float]:
        return [
            round((self.bin_edges[i] + self.bin_edges[i + 1]) / 2, 4)
            for i in range(len(self.counts))
        ]

    def as_dict(self) -> dict:
        return {
            "label": self.label,
            "bin_edges": [round(e, 4) for e in self.bin_edges],
            "bin_centers": self.bin_centers,
            "counts": self.counts,
            "x_label": self.x_label,
            "y_label": self.y_label,
        }


@dataclass
class ZPeakFit:
    """Result of a Gaussian fit to the Z boson peak region."""
    mean_gev: float           # fitted peak position
    sigma_gev: float          # fitted width (Gaussian σ)
    amplitude: float          # peak count
    chi2_ndf: float | None    # χ²/NDF of the fit (None if fit failed)
    pdg_mean_gev: float = Z_MASS_PDG
    pdg_width_gev: float = Z_WIDTH_PDG

    @property
    def deviation_from_pdg_gev(self) -> float:
        return self.mean_gev - self.pdg_mean_gev

    def as_dict(self) -> dict:
        return {
            "mean_gev": round(self.mean_gev, 3),
            "sigma_gev": round(self.sigma_gev, 3),
            "amplitude": round(self.amplitude, 1),
            "chi2_ndf": round(self.chi2_ndf, 3) if self.chi2_ndf else None,
            "pdg_mean_gev": self.pdg_mean_gev,
            "deviation_from_pdg_gev": round(self.deviation_from_pdg_gev, 3),
        }


@dataclass
class AnalysisResult:
    """Full output of the analysis pipeline."""
    config_used: dict
    cut_summary: CutSummary
    mass_histogram: HistogramData
    z_peak_histogram: HistogramData
    z_peak_fit: ZPeakFit | None
    processed_df: pd.DataFrame = field(repr=False)   # full tagged DataFrame
    z_df: pd.DataFrame = field(repr=False)            # Z candidates only

    def as_dict(self, include_df: bool = False) -> dict:
        d = {
            "cut_summary": self.cut_summary.as_dict(),
            "mass_histogram": self.mass_histogram.as_dict(),
            "z_peak_histogram": self.z_peak_histogram.as_dict(),
            "z_peak_fit": self.z_peak_fit.as_dict() if self.z_peak_fit else None,
        }
        if include_df:
            d["processed_records"] = self.processed_df.to_dict(orient="records")
        return d

class DimuonAnalysis:
    """
    Applies kinematic selection cuts, computes histograms, and fits the
    Z boson peak for a parsed dimuon DataFrame.

    All cut thresholds are read from config/pipeline.yaml — no code
    changes are needed to vary the selection.
    """

    def __init__(self, config: dict) -> None:
        self.cfg = config
        self.cuts = config["cuts"]
        self.hist_cfg = config["histogram"]

    def run(self, df: pd.DataFrame) -> AnalysisResult:
        """
        Run the full analysis pipeline on a parsed dimuon DataFrame.

        Steps
        -----
        1. Apply sequential kinematic cuts, tracking efficiency at each step
        2. Build invariant mass histograms (full spectrum + Z peak region)
        3. Fit a Gaussian to the Z peak to extract measured M_Z and σ
        """
        logger.info("Starting analysis on %d events …", len(df))

        # Step 1: cuts
        tagged_df, cut_summary = self._apply_cuts(df)

        # Step 2: histograms
        mass_hist = self._build_histogram(
            series=tagged_df["M"],
            n_bins=self.hist_cfg["n_bins"],
            lo=self.hist_cfg["mass_min_gev"],
            hi=self.hist_cfg["mass_max_gev"],
            label="Dimuon invariant mass spectrum (all passing cuts)",
        )

        z_df = tagged_df[tagged_df["z_candidate"]].copy()
        z_hist = self._build_histogram(
            series=z_df["M"],
            n_bins=self.hist_cfg["z_peak_bins"],
            lo=self.hist_cfg["z_peak_min_gev"],
            hi=self.hist_cfg["z_peak_max_gev"],
            label=f"Z boson peak region ({self.hist_cfg['z_peak_min_gev']}–"
                  f"{self.hist_cfg['z_peak_max_gev']} GeV)",
        )

        # Step 3: Z peak fit
        z_fit = self._fit_z_peak(z_hist) if len(z_df) >= 10 else None

        result = AnalysisResult(
            config_used=self.cfg,
            cut_summary=cut_summary,
            mass_histogram=mass_hist,
            z_peak_histogram=z_hist,
            z_peak_fit=z_fit,
            processed_df=tagged_df,
            z_df=z_df,
        )

        self._log_result(result)
        return result

    def _apply_cuts(self, df: pd.DataFrame) -> tuple[pd.DataFrame, CutSummary]:
        """Apply sequential cuts and return surviving events + cut summary."""
        c = self.cuts
        total = len(df)

        # -- CMS acceptance: |η| < η_max, pT > pT_min
        mask = (
            (df["eta1"].abs() < c["eta_max"])
            & (df["eta2"].abs() < c["eta_max"])
            & (df["pt1"] > c["pt_min_gev"])
            & (df["pt2"] > c["pt_min_gev"])
        )
        df = df[mask].copy()
        n_accept = len(df)
        logger.info("After acceptance cuts: %d (−%d)", n_accept, total - n_accept)

        # -- Opposite-sign requirement
        if c["require_opposite_sign"]:
            mask_os = (df["Q1"] * df["Q2"]) == -1
            df = df[mask_os].copy()
        n_os = len(df)
        logger.info("After opposite-sign: %d (−%d)", n_os, n_accept - n_os)

        # -- Global muon requirement
        if c["require_global_muon"]:
            mask_g = (df["Type1"].str.strip() == "G") | (df["Type2"].str.strip() == "G")
            df = df[mask_g].copy()
        n_global = len(df)
        logger.info("After global muon: %d (−%d)", n_global, n_os - n_global)

        # -- ΔR minimum separation
        d_phi = df["phi1"] - df["phi2"]
        d_phi = (d_phi + math.pi) % (2 * math.pi) - math.pi
        df = df.copy()
        df["delta_r"] = np.sqrt((df["eta1"] - df["eta2"])**2 + d_phi**2)
        mask_dr = df["delta_r"] > c["delta_r_min"]
        df = df[mask_dr].copy()
        n_dr = len(df)
        logger.info("After ΔR > %.1f: %d (−%d)", c["delta_r_min"], n_dr, n_global - n_dr)

        # -- Tag Z candidates (mass window)
        df["z_candidate"] = df["M"].between(
            c["z_window_low_gev"], c["z_window_high_gev"]
        )
        n_z = int(df["z_candidate"].sum())
        logger.info("Z candidates (M in %.0f–%.0f GeV): %d",
                    c["z_window_low_gev"], c["z_window_high_gev"], n_z)

        cut_summary = CutSummary(
            total_input=total,
            after_acceptance=n_accept,
            after_opposite_sign=n_os,
            after_global_muon=n_global,
            after_delta_r=n_dr,
            after_z_window=n_z,
        )

        return df, cut_summary

    @staticmethod
    def _build_histogram(
        series: pd.Series,
        n_bins: int,
        lo: float,
        hi: float,
        label: str,
    ) -> HistogramData:
        """Build a 1-D histogram from a pandas Series."""
        counts_arr, edges_arr = np.histogram(
            series.dropna(), bins=n_bins, range=(lo, hi)
        )
        return HistogramData(
            bin_edges=edges_arr.tolist(),
            counts=counts_arr.tolist(),
            label=label,
        )

    def _fit_z_peak(self, hist: HistogramData) -> ZPeakFit | None:
        """
        Fit a Gaussian to the Z peak histogram using least-squares.

        A Gaussian is a good approximation to the Breit-Wigner lineshape
        when detector resolution dominates the natural width (~2.5 GeV).
        The CMS momentum resolution at the Z mass is ~1–2 GeV, so the
        observed peak width is a convolution of the natural width and
        the experimental resolution.

        Returns None if the fit fails or there are too few events.
        """
        try:
            from scipy.optimize import curve_fit  # type: ignore
        except ImportError:
            logger.warning("scipy not available — skipping Z peak fit")
            return None

        centers = np.array(hist.bin_centers)
        counts = np.array(hist.counts, dtype=float)

        if counts.sum() < 10:
            logger.warning("Too few Z events for peak fit")
            return None

        def gaussian(x: np.ndarray, amp: float, mu: float, sigma: float) -> np.ndarray:
            return amp * np.exp(-0.5 * ((x - mu) / sigma) ** 2)

        # Initial guess: peak at PDG Z mass, σ ≈ 3 GeV, amplitude = max count
        p0 = [float(counts.max()), Z_MASS_PDG, 3.0]
        bounds = ([0, 80, 0.5], [counts.max() * 3, 100, 10])

        try:
            popt, _ = curve_fit(gaussian, centers, counts, p0=p0, bounds=bounds)
            amp, mu, sigma = popt

            # χ²/NDF: only bins with counts > 0
            mask = counts > 0
            expected = gaussian(centers[mask], *popt)
            chi2 = float(np.sum((counts[mask] - expected) ** 2 / expected))
            ndf = mask.sum() - 3
            chi2_ndf = chi2 / ndf if ndf > 0 else None

            logger.info(
                "Z peak fit: M = %.3f GeV  σ = %.3f GeV  χ²/NDF = %.2f",
                mu, abs(sigma), chi2_ndf or 0,
            )

            return ZPeakFit(
                mean_gev=round(float(mu), 4),
                sigma_gev=round(abs(float(sigma)), 4),
                amplitude=round(float(amp), 2),
                chi2_ndf=round(chi2_ndf, 3) if chi2_ndf else None,
            )

        except Exception as exc:
            logger.warning("Z peak fit failed: %s", exc)
            return None

    @staticmethod
    def _log_result(result: AnalysisResult) -> None:
        cs = result.cut_summary
        logger.info(
            "Analysis complete | input=%d | Z candidates=%d | efficiency=%.2f%%",
            cs.total_input, cs.after_z_window, cs.efficiency * 100,
        )
        if result.z_peak_fit:
            fit = result.z_peak_fit
            logger.info(
                "Z peak: measured M_Z = %.3f GeV  (PDG %.3f GeV, Δ = %+.3f GeV)",
                fit.mean_gev, fit.pdg_mean_gev, fit.deviation_from_pdg_gev,
            )