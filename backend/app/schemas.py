from typing import List, Optional
from pydantic import BaseModel, Field

class EventResponse(BaseModel):
    """Rigorous schema mapping directly to the SQLite 'events' table structure."""
    id: int
    run: int
    event: int
    invariant_mass: float = Field(..., description="Calculated invariant mass of the dimuon system in GeV")
    pt1: float = Field(..., description="Transverse momentum of the leading muon in GeV/c")
    pt2: float = Field(..., description="Transverse momentum of the trailing muon in GeV/c")
    eta1: float = Field(..., description="Pseudorapidity of muon 1")
    eta2: float = Field(..., description="Pseudorapidity of muon 2")
    phi1: float = Field(..., description="Azimuthal angle of muon 1 in radians")
    phi2: float = Field(..., description="Azimuthal angle of muon 2 in radians")
    px1: float
    py1: float
    pz1: float
    px2: float
    py2: float
    pz2: float
    e1: float = Field(..., description="Energy of muon 1 in GeV")
    e2: float = Field(..., description="Energy of muon 2 in GeV")
    q1: int = Field(..., description="Charge sign of muon 1 (+1 or -1)")
    q2: int = Field(..., description="Charge sign of muon 2 (+1 or -1)")
    type1: str = Field(..., description="Muon reconstruction type ('G', 'T', 'S')")
    type2: str = Field(..., description="Muon reconstruction type ('G', 'T', 'S')")
    delta_r: float = Field(..., description="Angular separation Delta R between tracks")
    z_candidate: int = Field(..., description="Boolean flag (1 or 0) indicating Z boson window acceptance")
    opp_sign: int = Field(..., description="Boolean flag (1 or 0) indicating opposite-sign charges")
    run_id: int = Field(..., description="Foreign key linking to the corresponding analysis run metadata")

    class Config:
        from_attributes = True
        populate_by_name = True


class HistogramResponse(BaseModel):
    """Schema for binned histogram distribution rendering."""
    bin_centers: List[float] = Field(..., description="Center values for each calculated GeV bin")
    counts: List[int] = Field(..., description="Event occurrences within each bin boundary")
    name: str


class PipelineStatsResponse(BaseModel):
    """Combines aggregated database stats with pipeline health and latency benchmarks."""
    total_events: int
    z_candidates: int
    mass_mean_gev: float
    mass_min_gev: float
    mass_max_gev: float
    z_mass_mean_gev: float
    pt1_mean_gev: float
    pt2_mean_gev: float
    trigger_rate_hz: Optional[float] = Field(None, description="Calculated HLT trigger rate")
    processing_latency_ms: Optional[float] = Field(None, description="Pipeline CPU execution latency per event batch")