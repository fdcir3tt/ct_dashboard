import pandas as pd

from common.db import upsert_df,create_table
from common.data import load_data,delete_files
from airflow.providers.postgres.hooks.postgres import PostgresHook



def load(clean_rates_df:pd.DataFrame,conn_str:str="dashboard_app_db"):

    hook = PostgresHook(postgres_conn_id=conn_str)
    print("Creando tabla de conversiones USD->MXN de moneda limpias...")

    # Categorías
    create_table(hook,"staging","tazas_clean",{"date"           :"DATE PRIMARY KEY",
                                               "exchange_rate"  :"NUMERIC"})
                                    
    print("Poblando tabla de conversiones USD->MXN de moneda limpias...")
    upsert_df(hook,"staging","tazas_clean",clean_rates_df,["date"])

    

def run_load(**context):
    path_strings = context["ti"].xcom_pull(task_ids="extract_past_rates", key="path_strings")
    
    print("Convirtiendo contexto a dataframes...")
    clean_rates_path = context["ti"].xcom_pull(task_ids="rates_merging", key="clean_rates_path")
    clean_rates_df = load_data(clean_rates_path)
    
    print("Comenzando carga de datos...")
    load(clean_rates_df)

    delete_files([clean_rates_path]+path_strings)