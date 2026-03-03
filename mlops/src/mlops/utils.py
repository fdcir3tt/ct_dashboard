import os
import datetime 
import pandas as pd
from pathlib import Path

Date = datetime.date
data_dir = Path('data')

def time_period(start_date: Date,
                end_date: Date = Date.today()) -> list[Date]:
    if start_date > end_date:
        raise ValueError("Fecha inicial debe tomar lugar antes que la fecha final de periodo")

    dates = []
    current = start_date

    while current <= end_date:
        dates.append(current)
        current += datetime.timedelta(days=1)

    return dates

def save_file_safe(data: pd.DataFrame, file_path: Path) -> None:
    
    file_path.parent.mkdir(parents=True, exist_ok=True)

    tmp_path = file_path.with_suffix(file_path.suffix + ".tmp")
    data.to_parquet(tmp_path, engine='pyarrow',index=False)

    os.replace(tmp_path, file_path)
