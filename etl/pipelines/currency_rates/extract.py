import pandas as pd

from common.data import save_data,generate_tmp_path_strings
from airflow.providers.postgres.hooks.postgres import PostgresHook

conn_str = "dashboard_app_db"

def extract()->dict[str,pd.DataFrame]:
    extracted_data = {}
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

    extracted_data["historic_exchange_rates"]= historic_exchange_rates
    extracted_data["extracted_rates"] = extracted_rates

    return extracted_data

def run_extract(**context):
    extracted_data = extract()
    path_strings = generate_tmp_path_strings(extracted_data)

    save_data(extracted_data,path_strings)
    context["ti"].xcom_push(key="path_strings",  value=path_strings)
    