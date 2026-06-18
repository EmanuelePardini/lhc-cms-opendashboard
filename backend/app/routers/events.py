from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from backend.app.dependencies import get_store
from backend.app.schemas import EventResponse
from pipeline.store import DimuonStore

router = APIRouter(prefix="/events", tags=["Kinematics"])


@router.get("", response_model=List[EventResponse])
def get_paginated_events(
        limit: int = Query(50, ge=1, le=1000, description="Page payload chunk size constraint"),
        offset: int = Query(0, ge=0, description="Paging iteration offset index"),
        z_candidate: Optional[bool] = Query(None, description="Filter explicitly by Z boson mass criteria acceptance"),
        mass_min: Optional[float] = Query(None, description="Lower bound invariant mass filter (GeV)"),
        mass_max: Optional[float] = Query(None, description="Upper bound invariant mass filter (GeV)"),
        pt_min: Optional[float] = Query(None, description="Filter out events where muon tracks fall below pT value"),
        run_id: Optional[int] = Query(None, description="Isolate results to a specific pipeline execution ID"),
        store: DimuonStore = Depends(get_store)
):
    """Retrieves an indexed, filtered, and paginated list of processed dimuon events."""
    df = store.query_events(
        z_candidate=z_candidate,
        mass_min=mass_min,
        mass_max=mass_max,
        pt_min=pt_min,
        run_id=run_id,
        limit=limit,
        offset=offset
    )
    # Efficiently serialize Pandas DataFrame to dictionary payload array
    return df.to_dict(orient="records")


@router.get("/{id}", response_model=EventResponse)
def get_single_event_by_id(id: int, store: DimuonStore = Depends(get_store)):
    """Fetches full kinematic calculations and tracking coordinates for a distinct event index."""
    # Reuse the store's embedded context manager for thread-safe isolation on ad-hoc scalar lookups
    with store._connect() as conn:
        row = conn.execute("SELECT * FROM events WHERE id = ?", (id,)).fetchone()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"Requested event particle record with index ID {id} does not exist."
        )

    return dict(row)