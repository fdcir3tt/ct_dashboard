import pandas as pd
from common.registry import register
from airflow.providers.postgres.hooks.postgres import PostgresHook

conn_str = "dashboard_app_db"
extracted_conditions = {"historic_exchange_rates" :"stop",
                        "extracted_rates"         :"stop",}
tag = "currency_rates"

@register(tag)
def extract_historic_exchange_rates(conn_str:str,**kwargs)->pd.DataFrame:
    hook = PostgresHook(postgres_conn_id=conn_str)
    try:
        historic_exchange_rates = hook.get_pandas_df("SELECT * FROM raw.tazas_historicas")
    except Exception as e:
        print("Tabla no encontrada, regresando DF vacío")
        historic_exchange_rates = pd.DataFrame()
    return historic_exchange_rates

@register(tag)
def extract_extracted_rates(conn_str:str,**kwargs)->pd.DataFrame:
    hook = PostgresHook(postgres_conn_id=conn_str)
    try:
        extracted_rates = hook.get_pandas_df("SELECT * FROM raw.tazas_extraidas")
    except Exception as e:
        print("Tabla no encontrada, regresando DF vacío")
        extracted_rates = pd.DataFrame()
    return extracted_rates
