import os
import datetime 
import pandas as pd
import yaml

from pathlib import Path
from typing import Any,Iterable
from dataclasses import dataclass

Date = datetime.date
data_dir = Path('data')

@dataclass
class ExperimentConfig:
    model : str
    metrics : Iterable[str]
    parameters : dict[str,Any] 
    time_period : tuple[Date,Date]
    time_unit : str='days'


def time_period(start_date: Date,end_date: Date = Date.today()) -> list[Date]:
    """
    Genera una lista de fechas en el periodo designado

    Parametros:
    - start_date: Date , Fecha inicio del periodo
    - end_date: Date , Fecha fin del periodo
    Regresa:
    - dates:list[Date], Lista de fechas entre 'start_date' y 'end_date'

    """
    if start_date > end_date:
        raise ValueError("Fecha inicial debe tomar lugar antes que la fecha final de periodo")

    dates = []
    current = start_date

    while current <= end_date:
        dates.append(current)
        current += datetime.timedelta(days=1)

    return dates

def save_file_safe(data: pd.DataFrame, file_path: Path) -> None:
    """
    Recibe un dataframe de pandas y la guarda de manera segura en ubicación específicada
    
    Parametros:
    - data: pandas.DataFrame , Datos que se quieren almacenar
    - file_path: pathlib.Path , Ubicación en donde se quieren almacenar los datos

    """
    file_path.parent.mkdir(parents=True, exist_ok=True)

    tmp_path = file_path.with_suffix(file_path.suffix + ".tmp")
    data.to_parquet(tmp_path, engine='pyarrow',index=False)

    os.replace(tmp_path, file_path)

def get_experiment_config(file_path:Path=Path('config.yml'))->ExperimentConfig:
    """
    Lee archivo de configuración de experimentos y lo carga como objeto de configuración

    Parametros:
    - file_path: pathlib.Path , Ubicación de archivo de configuración. 
    """
    if file_path.suffix=='.yml' or file_path.suffix=='.yaml':
        with open(file_path, mode='r') as f:
            config = yaml.safe_load(f)

    return ExperimentConfig(**config)