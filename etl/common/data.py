import json
import pandas as pd

from pathlib import Path
from typing import Any

def generate_tmp_path_strings(data_dict:dict[str,pd.DataFrame|list[dict[str,Any]]])->list[str]:
    path_strings = []
    for file_name,data in data_dict:
        if isinstance(data,pd.DataFrame):
            suffix=".parquet"
        if isinstance(data,list):
            suffix=".json"
        path_str = f"/tmp/{file_name}{suffix}"
        path_strings.append(path_str)
    return path_strings

def save_data(data:list[dict[str,Any]]|pd.DataFrame|dict[str,Any],path_strings:str|list[str])->None:
    # Un archivo
    if isinstance(path_strings,str):
        file_path = Path(path_strings)
        if isinstance(data,list):
            save_records(data,file_path)
        if isinstance(data,pd.DataFrame):
            data.to_parquet(file_path,engine="pyarrow")
    # Varios archivos
    if isinstance(path_strings,list):
        for path_str in path_strings:
            file_path = Path(path_str)
            file_name = str(file_path.stem)

            if file_path.suffix==".json":
                save_records(data[file_name],file_path)
            
            if file_path.suffix==".parquet":
                data[file_name].to_parquet(file_path,engine="pyarrow")
        

def load_data(path_strings:str|list[str])->list[dict[str,Any]]|pd.DataFrame|dict[str,Any]:
    # Un archivo
    if isinstance(path_strings,str):
        file_path = Path(path_strings)
        if file_path.suffix == ".json":
                data = load_records(file_path)
        if file_path.suffix == ".parquet":
                data = pd.read_parquet(file_path,engine="pyarrow")
        return data
    # Varios archivos
    data = {}
    for path_str in path_strings:
            file_path = Path(path_str)
            file_name = str(file_path.stem)
            if file_path.suffix == ".json":
                data[file_name] = load_records(file_path)
            if file_path.suffix == ".parquet":
                data[file_name] = pd.read_parquet(file_path,engine="pyarrow")
    return data 

def save_records(records:list[dict[str,Any]],file_path:Path)->None:
    with open(file_path, "w") as f:
        json.dump(records, f)

def load_records(file_path:Path)->list[dict[str,Any]]:
    with open(file_path) as f:
        records = json.load(f)
    return records

def delete_files(file_paths:str|list[str]|Path|list[Path])->None:
    if isinstance(file_paths, Path):
        file_paths.unlink()
        print(f"Archivo '{file_paths}' borrado correctamente!")
        return None
    
    if isinstance(file_paths, str):
        file_path = Path(file_paths)
        file_path.unlink()
        print(f"Archivo '{file_paths}' borrado correctamente!")
        return None
    
    for path in file_paths:
        if isinstance(path, str):
            file_path = Path(path)
            file_path.unlink()
            print(f"Archivo '{path}' borrado correctamente!") 
            continue
        path.unlink()
        print(f"Archivo '{path}' borrado correctamente!")        