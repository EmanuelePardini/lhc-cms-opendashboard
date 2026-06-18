from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.routers import events, analysis

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

# Route mounting
app.include_router(events.router)
app.include_router(analysis.router)