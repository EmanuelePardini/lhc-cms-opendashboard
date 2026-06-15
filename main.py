"""
main.py
-------
Integration test and demo for the LHC Stream Platform ingestion layer.

Runs the full pipeline:
    1. Download the CMS dimuon dataset (cached after first run)
    2. Parse into a DataFrame
    3. Print physics summary statistics
    4. Parse a sample of events into DimuonEvent objects
    5. Show a sample JSON payload (as the WebSocket will send it)
    6. Show which events are Z boson candidates

Run:
    python main.py

Run with larger dataset:
    python main.py --dataset dimuon_run2011a

Run without downloading (use cached file only):
    python main.py --no-download
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Add project root to path so imports work from any directory
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from ingestion.downloader import CERNOpenDataDownloader, DATASETS
from ingestion.parser import (
    DimuonCSVParser,
    Z_BOSON_MASS_GEV,
    Z_WINDOW_LOW_GEV,
    Z_WINDOW_HIGH_GEV,
    MUON_MASS_GEV,
)

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")

# ---------------------------------------------------------------------------
# Separator helpers
# ---------------------------------------------------------------------------
SEP = "─" * 60


def section(title: str) -> None:
    print(f"\n{SEP}")
    print(f"  {title}")
    print(SEP)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="LHC Stream Platform — ingestion test")
    parser.add_argument(
        "--dataset",
        default="dimuon_run2010b",
        choices=list(DATASETS.keys()),
        help="Dataset to use (default: dimuon_run2010b, ~100k events)",
    )
    parser.add_argument(
        "--cache-dir",
        default="data/cache",
        help="Directory for cached CSV files",
    )
    parser.add_argument(
        "--sample-events",
        type=int,
        default=5,
        help="Number of DimuonEvent objects to print as JSON (default: 5)",
    )
    parser.add_argument(
        "--max-rows",
        type=int,
        default=None,
        help="Max rows to parse (None = all). Use e.g. 10000 for quick test.",
    )
    args = parser.parse_args()

    # -----------------------------------------------------------------------
    # 1. Dataset info
    # -----------------------------------------------------------------------
    section("Dataset")
    info = DATASETS[args.dataset]
    print(f"  Name        : {info.name}")
    print(f"  Record      : opendata.cern.ch/record/{info.record_id}")
    print(f"  DOI         : {info.doi}")
    print(f"  Description : {info.description}")
    print(f"  ~Events     : {info.n_events_approx:,}")

    # -----------------------------------------------------------------------
    # 2. Download
    # -----------------------------------------------------------------------
    section("Download")
    downloader = CERNOpenDataDownloader(cache_dir=args.cache_dir)

    # List all datasets
    for ds in downloader.list_datasets():
        status = "✓ cached" if ds["cached"] else "  not cached"
        print(f"  [{status}]  {ds['name']}  (~{ds['n_events_approx']:,} events)")

    t0 = time.perf_counter()
    csv_path = downloader.get(args.dataset)
    elapsed = time.perf_counter() - t0

    size_mb = csv_path.stat().st_size / 1024 / 1024
    print(f"\n  File   : {csv_path}")
    print(f"  Size   : {size_mb:.1f} MB")
    print(f"  Time   : {elapsed:.2f}s")

    # -----------------------------------------------------------------------
    # 3. Parse into DataFrame
    # -----------------------------------------------------------------------
    section("DataFrame Parse")
    csv_parser = DimuonCSVParser(mass_tolerance=0.05)

    t0 = time.perf_counter()
    df = csv_parser.to_dataframe(csv_path, max_rows=args.max_rows)
    elapsed = time.perf_counter() - t0

    print(f"\n  Parsed {len(df):,} rows in {elapsed:.2f}s")
    print(f"  Columns: {list(df.columns)}")

    # -----------------------------------------------------------------------
    # 4. Physics summary
    # -----------------------------------------------------------------------
    section("Physics Summary")
    summary = csv_parser.summary(df)

    print(f"  Total events          : {summary['total_events']:,}")
    print(f"  Opposite-sign pairs   : {summary['opposite_sign_events']:,}")
    print(f"  Z candidates          : {summary['z_candidates']:,}")
    print(f"  Mean invariant mass   : {summary['mass_mean_gev']:.3f} GeV")
    print(f"  Std  invariant mass   : {summary['mass_std_gev']:.3f} GeV")
    if summary["mass_z_peak_mean_gev"]:
        print(f"  Z peak mean mass      : {summary['mass_z_peak_mean_gev']:.3f} GeV  "
              f"(PDG: {Z_BOSON_MASS_GEV:.3f} GeV)")
        deviation = abs(summary['mass_z_peak_mean_gev'] - Z_BOSON_MASS_GEV)
        print(f"  Deviation from PDG    : {deviation:.3f} GeV")
    print(f"  Mean pT (muon 1)      : {summary['pt1_mean_gev']:.3f} GeV/c")
    print(f"  Mean pT (muon 2)      : {summary['pt2_mean_gev']:.3f} GeV/c")
    print(f"  Global muon fraction  : {summary['global_muon_fraction']*100:.1f}%")

    # -----------------------------------------------------------------------
    # 5. Mass spectrum bins (rough histogram for terminal)
    # -----------------------------------------------------------------------
    section("Invariant Mass Spectrum (terminal histogram)")

    z_df = df[df["z_candidate"]]
    bins = [
        (0, 5, "η/ω resonances"),
        (5, 15, "Υ(upsilon) family"),
        (15, 40, "below Z (Drell-Yan)"),
        (40, 76, "off-peak region"),
        (76, 106, f"Z window ({Z_WINDOW_LOW_GEV}–{Z_WINDOW_HIGH_GEV} GeV)"),
        (106, 200, "above Z"),
    ]

    max_count = max(
        ((df["M"] >= lo) & (df["M"] < hi)).sum() for lo, hi, _ in bins
    )

    print(f"  {'Range':>10}  {'N':>8}  {'Bar':30}  Label")
    for lo, hi, label in bins:
        mask = (df["M"] >= lo) & (df["M"] < hi)
        n = mask.sum()
        bar_len = int(n / max_count * 28)
        bar = "█" * bar_len
        print(f"  {lo:>4}–{hi:<4} GeV  {n:>8,}  {bar:<28}  {label}")

    # -----------------------------------------------------------------------
    # 6. Sample DimuonEvent objects → JSON (WebSocket payload preview)
    # -----------------------------------------------------------------------
    section(f"Sample DimuonEvent JSON (first {args.sample_events} events)")
    events = csv_parser.to_events(csv_path, max_events=args.sample_events)

    for i, ev in enumerate(events):
        payload = ev.to_dict()
        print(f"\n  Event {i+1}/{args.sample_events}  "
              f"(Run {ev.run}, Event {ev.event})")
        print(f"    M            = {payload['invariant_mass']:.4f} GeV")
        print(f"    ΔR           = {payload['delta_r']:.4f}")
        print(f"    Opp sign     = {payload['is_opposite_sign']}")
        print(f"    Z candidate  = {payload['is_z_candidate']}")
        print(f"    Muon 1 type  = {payload['muon1']['type']}  "
              f"pT={payload['muon1']['pt']:.2f} GeV  "
              f"η={payload['muon1']['eta']:.3f}  "
              f"Q={payload['muon1']['charge']:+d}")
        print(f"    Muon 2 type  = {payload['muon2']['type']}  "
              f"pT={payload['muon2']['pt']:.2f} GeV  "
              f"η={payload['muon2']['eta']:.3f}  "
              f"Q={payload['muon2']['charge']:+d}")

        # Show first 3 track points for each muon
        t1 = payload["muon1"]["tracks"][:3]
        t2 = payload["muon2"]["tracks"][:3]
        print(f"    Track1[0:3]  = {t1}")
        print(f"    Track2[0:3]  = {t2}")

    # Full JSON of event 1
    print(f"\n  Full JSON payload for event 1:")
    payload0 = events[0].to_dict()
    # Truncate track points for readability
    payload0["muon1"]["tracks"] = payload0["muon1"]["tracks"][:3] + [{"...": "..."}]
    payload0["muon2"]["tracks"] = payload0["muon2"]["tracks"][:3] + [{"...": "..."}]
    print(json.dumps(payload0, indent=4))

    # -----------------------------------------------------------------------
    # 7. Z candidate sample
    # -----------------------------------------------------------------------
    section("Z Boson Candidate Events")
    z_events = csv_parser.to_events(csv_path, max_events=5000)
    z_candidates = [e for e in z_events if e.is_z_candidate]

    print(f"\n  Z candidates in first 5000 events: {len(z_candidates)}")
    print(f"  (Expected ~{int(5000 * summary['z_candidates'] / summary['total_events'])} "
          f"based on full dataset fraction)")

    if z_candidates:
        print(f"\n  Top 5 Z candidates by invariant mass:")
        top5 = sorted(z_candidates, key=lambda e: e.invariant_mass, reverse=True)[:5]
        for ev in top5:
            print(f"    Run={ev.run}  Event={ev.event}  "
                  f"M={ev.invariant_mass:.4f} GeV  "
                  f"ΔR={ev.delta_r:.3f}")

    # -----------------------------------------------------------------------
    # Done
    # -----------------------------------------------------------------------
    section("All checks passed ✓")
    print(f"\n  Ingestion layer is working correctly.")
    print(f"  Next step: implement pipeline/analysis.py")
    print(f"             → compute Z peak, apply configurable cuts")
    print()


if __name__ == "__main__":
    main()