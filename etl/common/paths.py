from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

ENV_DIR = BASE_DIR / "config" / "secrets"
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
