import logging
import sys
from pathlib import Path
from pipeline.store import DimuonStore
from pipeline.analysis import load_config

# Resolve Monorepo Root Directory (lhc-stream-platform/)
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
CONFIG_PATH = ROOT / "config" / "pipeline.yaml"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info(f"__file__    = {__file__}")
logger.info(f"ROOT        = {ROOT}")
logger.info(f"CONFIG_PATH = {CONFIG_PATH}")
logger.info(f"EXISTS      = {CONFIG_PATH.exists()}")

_config_cache = None
_store_instance = None

def get_config() -> dict:
    """Thread-safe lazy initialization for the pipeline YAML file configuration."""
    global _config_cache
    if _config_cache is None:
        _config_cache = load_config(str(CONFIG_PATH))
    return _config_cache

def get_store() -> DimuonStore:
    """Provides a unified DimuonStore singleton utilizing SQLite WAL mode for optimized read execution."""
    global _store_instance
    if _store_instance is None:
        cfg = get_config()
        db_relative_path = cfg.get("storage", {}).get("db_path", "processed/events.db")
        # Ensure the path is explicitly contextualized relative to the monorepo root
        _store_instance = DimuonStore(str(ROOT / db_relative_path))
    return _store_instance