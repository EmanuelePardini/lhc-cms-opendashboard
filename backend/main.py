from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.routers import events, analysis, datasets

app = FastAPI(
    title="LHC Open Dashboard - API Engine",
    description="High-performance backend routing infrastructure distributing CMS open-data kinematic analysis results.",
    version="1.1.0"
)

# Configure Cross-Origin Resource Sharing (CORS) rules for UI communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Strict domain constraints can be specified here prior to deployment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.get("/debug")
def debug():
    import os
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    return {
        "root": str(root),
        "config_exists": (root / "config" / "pipeline.yaml").exists(),
        "config_dir_exists": (root / "config").exists(),
        "config_dir_contents": os.listdir(root / "config") if (root / "config").exists() else "DIR NOT FOUND",
        "root_contents": os.listdir(root),
    }

# Route mounting
app.include_router(events.router)
app.include_router(analysis.router)
app.include_router(datasets.router)