import numpy as np
import pandas as pd

from common.dates import date
from common.data import save_data,load_data,delete_files

start_date = date("2020-01-01")
end_date = date("today")


def fill_exchange_rates(rates_dataframe: pd.DataFrame) -> pd.DataFrame:
    """
    Rellena valores faltantes en tabla de conversiones de moneda USD a MXN imputando 
    el valor promedio de los ultimos dos valores antes de la conversión faltante. 

    Parametros:
    ----------
    rates_dataframe: pandas.DataFrame 
        Tabla de conversiones de moneda a rellenar

    Regresa:
    -------
    df: pandas.DataFrame
        Tabla imputada de conversiones de moneda
    """
    df = rates_dataframe.copy()

    # Step 1: ensure proper ordering
    df = df.sort_index()

    # Step 2: forward fill first (handles leading NaNs safely)
    df["exchange_rate"] = df["exchange_rate"].ffill()

    # Step 3: fill remaining NaNs (if any at start)
    df["exchange_rate"] = df["exchange_rate"].bfill()

    # Step 4: optional smoothing using rolling mean of last 2 values
    df["exchange_rate"] = df["exchange_rate"].fillna(
        df["exchange_rate"].rolling(2, min_periods=1).mean()
    )

    return df


def transform(historic_df:pd.DataFrame,extracted_rates_df:pd.DataFrame)->pd.DataFrame:
    historic_df["date"] = pd.to_datetime(historic_df["date"], utc=True)
    extracted_rates_df["date"] = pd.to_datetime(extracted_rates_df["date"], utc=True)
    
    period = pd.DataFrame( {"date": pd.date_range(start=start_date, end=end_date, freq="D")} )
    if historic_df.empty:
        merged = (period
                        .merge(extracted_rates_df.reset_index(),how="left",on="date",suffixes=("", "_fill"))
                    )
    else:    
        merged = (period
                        .merge(historic_df, how="left", on="date")
                        .merge(extracted_rates_df.reset_index(),how="left",on="date",suffixes=("", "_fill"))
                    )
    print(merged.head())
    merged["exchange_rate"] = merged["exchange_rate"].fillna(merged["exchange_rate_fill"])
    merged = merged.drop(columns=["exchange_rate_fill"])
    
    filled_rates = fill_exchange_rates(rates_dataframe=merged)
    filled_rates = filled_rates.drop(columns=["index","fallback"])
    filled_rates["date"] = filled_rates["date"].dt.date
    return filled_rates
    
    

def run_transform(**context):
    path_strings = context["ti"].xcom_pull(task_ids="extract_past_rates", key="path_strings")
    extracted_data = load_data(path_strings)

    raw_exchange_rates_df = extracted_data["extracted_rates"]
    historic_rates_df     = extracted_data["historic_exchange_rates"]
    
    transformed_data = transform(historic_rates_df,raw_exchange_rates_df)
    
    clean_rates_path = "/tmp/clean_rates.parquet"
    save_data(transformed_data,clean_rates_path)
    
    context["ti"].xcom_push(key="clean_rates_path", value=clean_rates_path)
    
    delete_files(path_strings)