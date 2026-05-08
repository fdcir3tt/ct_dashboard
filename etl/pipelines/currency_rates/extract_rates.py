import os
import json
import requests
import numpy as np
import pandas as pd

from dotenv import load_dotenv
from common.dates import date
from common.paths import ENV_DIR
from common.db import create_table,upsert_df
from airflow.providers.postgres.hooks.postgres import PostgresHook

load_dotenv(ENV_DIR / ".env")
api_key = os.getenv("EXCHANGE_API_KEY")
today = date("today")
conn_str = "dashboard_app_db"


def get_usd_to_mxn(key:str)->float|None:
    """
    Se conecta a página de conversiones de moneda y extrae la conversión de USD a MXN 
    más actual.

    Parametros:
    Regresa:
    - rate: float, Conversión de moneda USD a MXN
    """
    
    url = "https://api.fxratesapi.com/latest"
    params = {
            "api_key": key,
            "base": "USD",
            "currencies": "MXN",
            "resolution": "1d",
            "amount": 1,
            "places": 6,
            "format": "json"
            }
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException:
        print("FX rates API request failed")
        return None

    try:
        data = response.json()
    except json.JSONDecodeError:
        print(f"Failed to decode JSON from FX rates API,\nresponse_text: {response.text}")
        return None

    try:
        rate = data["rates"]["MXN"]
        return rate
    except KeyError:
        print(f"MXN rate missing from API response \nresponse_json: {data}")
        return None

def extract()->float|None:
    try:
        rate = get_usd_to_mxn(api_key)
    except Exception as e:
        print(e)
        rate = None
    return rate

def transform(data:pd.DataFrame,rate:float|None)->pd.DataFrame:
   
    if rate is not None:
        new_row = pd.DataFrame({"date": [today],"exchange_rate": [rate],"fallback": [""]})
        if data.empty:
            return new_row
        return pd.concat([data,new_row])
    
    elif len(data)>=2:
        fallback_rate = np.mean(data["exchange_rate"].tail(2))
        fallback = "average"
    else: 
        fallback_rate = data["exchange_rate"].iloc[-1]
        fallback = "previous_rate"

    new_row = pd.DataFrame({"date":[today],"exchange_rate":[fallback_rate],"fallback":[fallback]})
    return pd.concat([data,new_row])

def load(hook,data:pd.DataFrame):
    if len(data)==1:
        create_table(hook,"raw","tazas_extraidas",{"date"         :"DATE PRIMARY KEY",
                                                   "exchange_rate":"NUMERIC",
                                                   "fallback"     :"VARCHAR"})
        upsert_df(hook,"raw","tazas_extraidas",data,["date"])

    upsert_df(hook,"raw","tazas_extraidas",data,["date"])

def run_extract_rates():
    extracted_rate = extract()
    hook = PostgresHook(postgres_conn_id=conn_str)

    try:
        df = hook.get_pandas_df("SELECT * FROM raw.tazas_extraidas")
    except Exception as e:
        print("Table not found, returning empty DF")
        df = pd.DataFrame()

    transformed_data = transform(df,extracted_rate)
    load(hook,transformed_data)
    
