import re
from fastapi import APIRouter, Depends
from backend.app.dependencies import get_store
from pipeline.store import DimuonStore

router = APIRouter(prefix="/datasets", tags=["Datasets"])


@router.get("")
def list_datasets(store: DimuonStore = Depends(get_store)):
    with store._connect() as conn:
        rows = conn.execute("""
            SELECT id, dataset, timestamp, n_events, n_z_candidates
            FROM analysis_runs
            ORDER BY id ASC
        """).fetchall()

    result = []
    for r in rows:
        dataset_name = r["dataset"]

        # Estrae l'anno (4 cifre)
        year_match = re.search(r"\d{4}", dataset_name)

        if year_match:
            year = int(year_match.group())
            energy = "8 TeV" if year == 2012 else "7 TeV"

            # Cerca una lettera di "Run" (es. 'run2010b' -> 'B', 'run2011a' -> 'A')
            # Cerca una lettera singola (a-z) subito dopo l'anno o dopo la parola 'run'
            run_match = re.search(r"run\d{4}([a-zA-Z])|\d{4}([a-zA-Z])", dataset_name)

            run_letter = ""
            if run_match:
                # Prende il gruppo che ha catturato la lettera (può essere il primo o il secondo)
                letter = run_match.group(1) or run_match.group(2)
                if letter:
                    run_letter = f" — Run {letter.upper()}"

            label = f"CMS Dimuon {year}{run_letter}"
            desc = f"Dimuon events reconstructed from CMS proton-proton collisions at {energy} ({year}). Ideal for invariant mass spectrum analysis."
        else:
            # Fallback se il nome è custom
            year = "—"
            energy = "—"
            label = dataset_name.replace("_", " ").title()
            desc = "Manually loaded dataset from CERN Open Data."

        result.append({
            "id": r["id"],
            "dataset": dataset_name,
            "label": label,
            "energy": energy,
            "year": year,
            "desc": desc,
            "timestamp": r["timestamp"],
            "n_events": r["n_events"],
            "n_z_candidates": r["n_z_candidates"],
        })

    return result