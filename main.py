import argparse
import json
import logging
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from ingestion.downloader import CERNOpenDataDownloader, DATASETS
from ingestion.parser import DimuonCSVParser
from pipeline.analysis import DimuonAnalysis, load_config
from pipeline.store import DimuonStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)-22s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")

SEP = "═" * 64

def section(title: str) -> None:
    print(f"\n{SEP}")
    print(f"  {title}")
    print(SEP)

def sub(label: str, value) -> None:
    print(f"  {label:<36} {value}")



def main() -> None:
    ap = argparse.ArgumentParser(description="LHC Open Dashboard — full pipeline test")
    ap.add_argument("--dataset", default="dimuon_run2011a", choices=list(DATASETS.keys()))
    ap.add_argument("--config", default="config/pipeline.yaml")
    ap.add_argument("--max-rows", type=int, default=None,
                    help="Limit rows parsed (None = all). Use 5000 for fast test.")
    ap.add_argument("--stream-sample", type=int, default=3,
                    help="Number of batches to print iter")
    args = ap.parse_args()

    t_total = time.perf_counter()

    # 0. Config
    section("0 · Configuration")
    cfg = load_config(args.config)
    sub("Dataset", args.dataset)
    sub("Config file", args.config)
    sub("Max rows", args.max_rows or "all")
    sub("pT_min [GeV]", cfg["cuts"]["pt_min_gev"])
    sub("|η|_max", cfg["cuts"]["eta_max"])
    sub("Z window [GeV]", f"{cfg['cuts']['z_window_low_gev']}–{cfg['cuts']['z_window_high_gev']}")
    sub("ΔR_min", cfg["cuts"]["delta_r_min"])
    sub("DB path", cfg["storage"]["db_path"])

    # Override max_rows from CLI if provided
    if args.max_rows:
        cfg["ingestion"]["max_rows"] = args.max_rows

    # 1. Download
    section("1 · Download")
    downloader = CERNOpenDataDownloader(cache_dir=cfg["ingestion"]["cache_dir"])
    t0 = time.perf_counter()
    csv_path = downloader.get(args.dataset)
    sub("CSV path", csv_path)
    sub("File size", f"{csv_path.stat().st_size / 1024 / 1024:.1f} MB")
    sub("Time", f"{time.perf_counter() - t0:.2f}s")

    # 2. Parse
    section("2 · Parse")
    parser = DimuonCSVParser()
    t0 = time.perf_counter()
    df = parser.to_dataframe(csv_path, max_rows=cfg["ingestion"].get("max_rows"))
    elapsed = time.perf_counter() - t0
    sub("Rows parsed", f"{len(df):,}")
    sub("Columns", len(df.columns))
    sub("Time", f"{elapsed:.2f}s  ({len(df)/elapsed:,.0f} rows/s)")
    sub("M range [GeV]", f"{df['M'].min():.3f} – {df['M'].max():.3f}")
    sub("Mean pT1 [GeV/c]", f"{df['pt1'].mean():.3f}")
    sub("Opp-sign pairs", f"{(df['Q1']*df['Q2']==-1).sum():,}")

    # 3. Analyse
    section("3 · Analysis")
    analysis = DimuonAnalysis(cfg)
    t0 = time.perf_counter()
    result = analysis.run(df)
    elapsed = time.perf_counter() - t0

    cs = result.cut_summary
    sub("Time", f"{elapsed:.2f}s")
    print()
    print("  Cut flow:")
    print(f"    {'Input':<30} {cs.total_input:>8,}")
    print(f"    {'After acceptance':<30} {cs.after_acceptance:>8,}  "
          f"({cs.after_acceptance/cs.total_input*100:.1f}%)")
    print(f"    {'After opposite-sign':<30} {cs.after_opposite_sign:>8,}  "
          f"({cs.after_opposite_sign/cs.total_input*100:.1f}%)")
    print(f"    {'After global muon':<30} {cs.after_global_muon:>8,}  "
          f"({cs.after_global_muon/cs.total_input*100:.1f}%)")
    print(f"    {'After ΔR > ' + str(cfg['cuts']['delta_r_min']):<30} {cs.after_delta_r:>8,}  "
          f"({cs.after_delta_r/cs.total_input*100:.1f}%)")
    print(f"    {'Z candidates (mass window)':<30} {cs.after_z_window:>8,}  "
          f"({cs.after_z_window/cs.total_input*100:.1f}%)")

    if result.z_peak_fit:
        fit = result.z_peak_fit
        print()
        print("  Z peak fit (Gaussian):")
        sub("  Measured M_Z", f"{fit.mean_gev:.3f} GeV")
        sub("  PDG M_Z", f"{fit.pdg_mean_gev:.3f} GeV")
        sub("  Deviation", f"{fit.deviation_from_pdg_gev:+.3f} GeV")
        sub("  σ (fitted width)", f"{fit.sigma_gev:.3f} GeV")
        if fit.chi2_ndf:
            sub("  χ²/NDF", f"{fit.chi2_ndf:.3f}")

    # Terminal mass histogram
    print()
    print("  Mass spectrum (all passing cuts):")
    hist = result.mass_histogram
    centers = hist.bin_centers
    counts = hist.counts
    max_c = max(counts) if counts else 1
    # Print every 5th bin for readability
    print(f"  {'M [GeV]':>10}  {'N':>7}  bar")
    for i in range(0, len(centers), max(1, len(centers)//20)):
        bar = "█" * int(counts[i] / max_c * 30)
        print(f"  {centers[i]:>10.1f}  {counts[i]:>7,}  {bar}")

    # 4. Persist
    section("4 · Persist to SQLite")
    store = DimuonStore(cfg["storage"]["db_path"])
    t0 = time.perf_counter()
    run_id = store.save_analysis(
        result,
        dataset_name=args.dataset
    )
    elapsed = time.perf_counter() - t0
    sub("run_id", run_id)
    sub("DB path", cfg["storage"]["db_path"])
    sub("DB size", f"{Path(cfg['storage']['db_path']).stat().st_size / 1024 / 1024:.2f} MB")
    sub("Time", f"{elapsed:.2f}s")

    # 5. Query — verify REST-style access
    section("5 · Query (REST simulation)")

    # All events, paginated
    t0 = time.perf_counter()
    events_page = store.query_events(limit=10, offset=0)
    sub("GET /events?limit=10", f"{len(events_page)} rows  ({(time.perf_counter()-t0)*1000:.1f}ms)")

    # Z candidates only
    t0 = time.perf_counter()
    z_page = store.query_events(z_candidate=True, limit=10)
    sub("GET /events?z_candidate=true", f"{len(z_page)} rows  ({(time.perf_counter()-t0)*1000:.1f}ms)")

    # Mass range filter
    t0 = time.perf_counter()
    mass_range = store.query_events(mass_min=85.0, mass_max=97.0, limit=100)
    sub("GET /events?mass_min=85&mass_max=97", f"{len(mass_range)} rows  ({(time.perf_counter()-t0)*1000:.1f}ms)")

    # Histograms
    t0 = time.perf_counter()
    mass_hist_dict = store.get_histogram("mass_spectrum")
    sub("GET /histogram/mass", f"{len(mass_hist_dict['counts'])} bins  ({(time.perf_counter()-t0)*1000:.1f}ms)")

    t0 = time.perf_counter()
    z_hist_dict = store.get_histogram("z_peak")
    sub("GET /histogram/z_peak", f"{len(z_hist_dict['counts'])} bins  ({(time.perf_counter()-t0)*1000:.1f}ms)")

    # Stats
    t0 = time.perf_counter()
    stats = store.get_stats()
    sub("GET /stats", f"({(time.perf_counter()-t0)*1000:.1f}ms)")
    print()
    for k, v in stats.items():
        print(f"    {k:<30} {v}")

    # Run metadata
    run_meta = store.get_latest_run()
    print()
    sub("Latest run timestamp", run_meta["timestamp"])
    sub("Latest run dataset", run_meta["dataset"])

    section("6 · Summary")
    total_time = time.perf_counter() - t_total
    sub("Total wall time", f"{total_time:.2f}s")
    sub("Events processed", f"{cs.total_input:,}")
    sub("Events/second", f"{cs.total_input / total_time:,.0f}")
    sub("Z candidates found", f"{cs.after_z_window:,}")
    sub("DB written to", cfg["storage"]["db_path"])
    if result.z_peak_fit:
        sub("Measured M_Z", f"{result.z_peak_fit.mean_gev:.3f} GeV  "
            f"(PDG: {result.z_peak_fit.pdg_mean_gev:.3f} GeV)")

    print()
    print("  All stages passed ✓")
    print("  Next: implement backend/main.py (FastAPI)")
    print()


if __name__ == "__main__":
    main()