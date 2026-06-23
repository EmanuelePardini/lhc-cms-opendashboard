# LHC CMS Open Dashboard

▶️ **[Visit the live demo](https://www.lhc-cms-opendashboard-fe.onrender.com)**

A complete pipeline from data ingestion to 3D visualization  for analyzing real **dimuon** collision events recorded by the **CMS** experiment at the Large Hadron Collider (CERN), published on the [CERN Open Data Portal](https://opendata.cern.ch/).

The project downloads the public datasets, applies the kinematic selection cuts typical of a particle physics analysis, fits the **Z⁰ boson** mass peak, stores the results in SQLite, exposes them through a REST API (FastAPI), and makes them explorable in an interactive 3D viewer (React + Three.js) that reconstructs the detector and the particle tracks.

## Demo video

[![Watch the demo video](https://img.youtube.com/vi/j7ScqictZTo/maxresdefault.jpg)](https://www.youtube.com/watch?v=j7ScqictZTo)

▶️ **[Watch the demo on YouTube](https://www.youtube.com/watch?v=j7ScqictZTo)**

## Table of contents

- [What the project does](#what-the-project-does)
- [Architecture](#architecture)
- [Dataset](#dataset)
- [Physics implemented](#physics-implemented)
- [Tech stack](#tech-stack)
- [Repository structure](#repository-structure)
- [Installation](#installation)
- [Usage](#usage)
- [REST API](#rest-api)
- [Configuration](#configuration)
- [Data credits and license](#data-credits-and-license)

## What the project does

1. **Downloads** a public CMS dimuon dataset from the CERN Open Data Portal (with local caching and resumable downloads).
2. **Parses** the CSV into a pandas DataFrame holding all kinematic quantities for each muon (energy, momentum, pseudorapidity, azimuthal angle, charge, reconstruction type).
3. **Applies a chain of selection cuts** (detector acceptance, opposite charge, "global muon" quality, angular separation ΔR) to isolate Z boson candidates.
4. **Runs a Gaussian fit** on the invariant mass peak in the 76–106 GeV region to measure the Z boson mass and compare it against the PDG reference value (91.188 GeV).
5. **Persists** events, histograms, and run metadata for every run into a SQLite database.
6. **Exposes the results** through a REST API (FastAPI) with paginated, filterable endpoints ready to be consumed by a frontend.
7. **Visualizes** every single event in an interactive 3D scene that reconstructs a simplified version of the CMS detector (barrel, endcaps, beam pipe) and animates the two muons' helical trajectories inside the magnetic field.

## Architecture

```
CERN Open Data Portal (CSV)
        │
        ▼
┌─────────────────┐
│   ingestion/     │  download + cache + CSV parsing → DataFrame
└─────────────────┘
        │
        ▼
┌─────────────────┐
│   pipeline/      │  kinematic cuts, histograms, Z peak fit
│   analysis.py    │
└─────────────────┘
        │
        ▼
┌─────────────────┐
│   pipeline/      │  SQLite persistence (events, histograms, analysis_runs)
│   store.py       │
└─────────────────┘
        │
        ▼
┌─────────────────┐
│   backend/       │  FastAPI REST API (events, histograms, stats, datasets)
│   (FastAPI)      │
└─────────────────┘
        │
        ▼
┌─────────────────┐
│   frontend/      │  React + Three.js dashboard: 3D detector viewer,
│   (React+Three)  │  event/dataset selector, stats, cuts configuration
└─────────────────┘
```

`main.py`, at the repo root, runs the entire pipeline end-to-end from the command line (download → parsing → analysis → persistence → verification queries), which is useful for testing the system without spinning up the backend and frontend.

## Dataset

The data comes from the CERN Open Data Portal and contains real dimuon events reconstructed by the CMS detector:

| Dataset | Run | Events (~) | Energy | Record |
|---|---|---|---|---|
| `dimuon_run2010b` | Run2010B | 100,000 | 7 TeV | [opendata.cern.ch/record/700](https://opendata.cern.ch/record/700) |
| `dimuon_run2011a` (default) | Run2011A | 986,000 | 7 TeV | [opendata.cern.ch/record/545](https://opendata.cern.ch/record/545) |

Each row represents an event with two muon candidates and the precomputed invariant mass (range 0.3–300 GeV), ideal for observing the J/ψ, Υ, and Z⁰ resonances.

## Physics implemented

- **Acceptance cuts**: |η| < 2.4, pT > 3 GeV/c for both muons.
- **Opposite charge**: requires Q1 · Q2 = −1.
- **"Global" muon**: at least one muon reconstructed in both the inner tracker and the muon chambers.
- **Angular separation**: ΔR = √(Δη² + Δφ²) > 0.3 to reject overlapping tracks.
- **Z mass window**: 76–106 GeV for Z candidate tagging.
- **Gaussian fit of the Z peak** (approximation of the Breit-Wigner distribution) to extract the measured mass, width σ, and χ²/NDF, compared against PDG values (M_Z = 91.188 GeV, Γ_Z = 2.495 GeV).

## Tech stack

**Backend / pipeline**
- Python 3.9+
- FastAPI + Pydantic (REST API)
- pandas, NumPy (data processing)
- SciPy (Gaussian fit of the Z peak)
- SQLite (persistence, WAL mode)
- PyYAML (configuration)
- Requests (dataset download)

**Frontend**
- React 18 + Vite
- Three.js (3D detector scene and track animation)
- Recharts (charts/histograms)
- lucide-react (icons)

## Repository structure

```
.
├── main.py                  # end-to-end pipeline run from the CLI
├── config/
│   └── pipeline.yaml        # kinematic cuts, paths, storage parameters
├── ingestion/
│   ├── downloader.py        # CSV download/cache from the CERN Open Data Portal
│   └── parser.py            # CSV parsing → pandas DataFrame
├── pipeline/
│   ├── analysis.py          # cuts, histograms, Z peak fit
│   └── store.py             # SQLite persistence and queries
├── backend/
│   ├── main.py               # FastAPI app, router mounting
│   └── app/
│       ├── dependencies.py   # shared config and store (dependency injection)
│       ├── schemas.py        # Pydantic response models
│       └── routers/
│           ├── events.py     # /events
│           ├── analysis.py   # /histogram/mass, /stats, /config
│           └── datasets.py   # /datasets
├── frontend/
│   └── src/
│       ├── LHCViewer.jsx     # main dashboard component
│       ├── three/            # 3D scene construction, detector, helical tracks
│       ├── components/       # draggable panels, selectors, legend, stats
│       └── hooks/useEvents.js# REST API calls to the backend
└── data/
    ├── cache/                # CSVs downloaded from the CERN Open Data Portal
    └── processed/            # SQLite database with processed events/histograms
```

## Installation

### Requirements
- Python 3.9 or higher
- Node.js 18+ and npm

### Backend

```bash
# from the repository root
pip install fastapi "uvicorn[standard]" pandas numpy requests pyyaml scipy pydantic --break-system-packages

# start the REST API (port 8000, expected by the frontend)
uvicorn backend.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The app will be available at `http://localhost:5173` and will talk to the backend at `http://localhost:8000`.

## Usage

To test the entire pipeline from the command line, without starting the backend/frontend:

```bash
python main.py --dataset dimuon_run2011a --max-rows 5000
```

Main options:

| Flag | Description | Default |
|---|---|---|
| `--dataset` | dataset to download/analyze | `dimuon_run2011a` |
| `--config` | path to the YAML configuration file | `config/pipeline.yaml` |
| `--max-rows` | limits the number of rows parsed (useful for quick tests) | all |

The script prints the cut-flow as each selection is applied, the outcome of the Z peak fit, a terminal histogram of the mass spectrum, and simulates a few REST queries (`GET /events`, `GET /histogram/mass`, `GET /stats`) to verify the full data cycle.

## REST API

Once the backend is running (`uvicorn backend.main:app`), interactive documentation is available at `http://localhost:8000/docs`.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/events` | paginated events, filterable by `z_candidate`, `mass_min`/`mass_max`, `pt_min`, `run_id` |
| `GET` | `/events/{id}` | full kinematic detail of a single event |
| `GET` | `/histogram/mass` | invariant mass spectrum histogram |
| `GET` | `/stats` | aggregated run statistics (means, Z mass, etc.) |
| `GET` | `/config` | currently active kinematic cuts configuration |
| `GET` | `/datasets` | list of processed and available datasets |

## Configuration

Physics selection parameters are centralized in `config/pipeline.yaml` and require no code changes:

```yaml
cuts:
  pt_min_gev: 3.0
  eta_max: 2.4
  z_window_low_gev: 76.0
  z_window_high_gev: 106.0
  delta_r_min: 0.3

storage:
  db_path: "data/processed/events.db"
```

## Data credits and license

The data used is distributed by the **CERN Open Data Portal** under a Creative Commons CC0 license:

- McCauley, Thomas (2014). *Dimuon event information derived from the Run2010B public Mu dataset.* DOI: [10.7483/OPENDATA.CMS.CB8H.MFFA](https://doi.org/10.7483/OPENDATA.CMS.CB8H.MFFA)
- *Run2011A DoubleMu dataset.* DOI: [10.7483/OPENDATA.CMS.IYVQ.1J0G](https://doi.org/10.7483/OPENDATA.CMS.IYVQ.1J0G)

This project is for educational/demonstrative purposes and is not affiliated with CERN or the CMS Collaboration.
