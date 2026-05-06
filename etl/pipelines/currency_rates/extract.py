import pandas as pd

from airflow.providers.postgres.hooks.postgres import PostgresHook

conn_str = "dashboard_app_db"

def extract()->tuple[pd.DataFrame,pd.DataFrame]:
    hook = PostgresHook(postgres_conn_id=conn_str)
    try:
        historic_exchange_rates = hook.get_pandas_df("SELECT * FROM raw.tazas_historicas")
    except Exception as e:
        print("Tabla no encontrada, regresando DF vacío")
        historic_exchange_rates = pd.DataFrame()
    
    try:
        extracted_rates = hook.get_pandas_df("SELECT * FROM raw.tazas_extraidas")
    except Exception as e:
        print("Tabla no encontrada, regresando DF vacío")
        extracted_rates = pd.DataFrame()

    return historic_exchange_rates,extracted_rates

def run_extract(**context):
    extracted_data = extract()
    context["ti"].xcom_push(key="historic_exchange_rates",  value=extracted_data[0].to_dict(orient="records"))
    context["ti"].xcom_push(key="extracted_exchange_rates", value=extracted_data[1].to_dict(orient="records"))
    