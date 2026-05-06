import numpy as np
import pandas as pd

from common.dates import date

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
    return filled_rates
    
    

def run_transform(**context):
    
    historic_rates_df     = pd.DataFrame(context["ti"].xcom_pull(task_ids="extract_past_rates", key="historic_exchange_rates"))
    raw_exchange_rates_df = pd.DataFrame(context["ti"].xcom_pull(task_ids="extract_past_rates", key="extracted_exchange_rates"))
    
    transformed_data = transform(historic_rates_df,raw_exchange_rates_df)
    transformed_data["date"] = transformed_data["date"].dt.date
    print(transformed_data.head())
    context["ti"].xcom_push(key="clean_rates", value=transformed_data.to_dict(orient="records"))