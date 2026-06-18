from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from backend.app.dependencies import get_store, get_config
from backend.app.schemas import HistogramResponse, PipelineStatsResponse
from pipeline.store import DimuonStore

router = APIRouter(tags=["Analysis Engine"])


@router.get("/histogram/mass", response_model=HistogramResponse)
def get_invariant_mass_histogram(store: DimuonStore = Depends(get_store)):
    """Retrieves structural distribution array counts of the overall dimuon mass spectrum."""
    hist_data = store.get_histogram(name="mass_spectrum")
    if not hist_data:
        raise HTTPException(
            status_code=404,
            detail="The invariant mass spectrum distribution payload is unavailable or has not been computed yet."
        )

    return HistogramResponse(
        bin_centers=hist_data["bin_centers"],
        counts=hist_data["counts"],
        name="mass_spectrum"
    )


@router.get("/stats", response_model=PipelineStatsResponse)
def get_aggregated_pipeline_statistics(store: DimuonStore = Depends(get_store)):
    """Computes aggregate physics distributions and framework latency diagnostics for the current dataset run."""
    stats = store.get_stats()
    if not stats:
        raise HTTPException(status_code=404, detail="No analytical summaries are present inside the database schema.")

    latest_run = store.get_latest_run()
    trigger_rate = None
    latency = None

    # Safely extract optional performance telemetry inside run summaries if configured
    if latest_run and latest_run.get("cut_summary_json"):
        summary = latest_run["cut_summary_json"]
        trigger_rate = summary.get("trigger_rate_hz", None)
        latency = summary.get("processing_latency_ms", None)

    return PipelineStatsResponse(
        total_events=stats["total_events"],
        z_candidates=stats["z_candidates"],
        mass_mean_gev=stats["mass_mean_gev"],
        mass_min_gev=stats["mass_min_gev"],
        mass_max_gev=stats["mass_max_gev"],
        z_mass_mean_gev=stats["z_mass_mean_gev"],
        pt1_mean_gev=stats["pt1_mean_gev"],
        pt2_mean_gev=stats["pt2_mean_gev"],
        trigger_rate_hz=trigger_rate,
        processing_latency_ms=latency
    )


@router.get("/config", response_model=Dict[str, Any])
def get_active_pipeline_configuration(config: dict = Depends(get_config)):
    """Provides a read-only payload state of the YAML configuration filters currently active."""
    return config