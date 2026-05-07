import json
import pandas as pd

from pathlib import Path
from typing import Any

def load_extracted_data(path_strings:list[str])->dict[str,Any]:
    extracted_data = {}
    for path_str in path_strings:
            file_path = Path(path_str)
            file_name = str(file_path.stem)
            if file_path.suffix == ".json":
                extracted_data[file_name] = load_records(file_path)
            if file_path.suffix == ".parquet":
                extracted_data[file_name] = pd.read_parquet(file_path,engine="pyarrow")

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