import json

from typing import Any
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

ENV_DIR = BASE_DIR / "config" / "secrets"
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

def save_records(records:list[dict[str,Any]],file_path:Path)->None:
    with open(file_path, "w") as f:
        json.dump(records, f)

def load_records(file_path:Path)->list[dict[str,Any]]:
    with open(file_path) as f:
        records = json.load(f)
    return records

def delete_files(file_paths:Path|list[Path])->None:
    if isinstance(file_paths, Path):
        file_paths.unlink()
        print(f"Archivo '{file_paths}' borrado correctamente!")
        return None
    for path in file_paths:
        path.unlink()
        print(f"Archivo '{path}' borrado correctamente!") 