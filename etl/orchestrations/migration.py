# Tables:

# branches    -> raw.almacenes
# conversion_usd_mxn  -> staging.tazas_clean
# facturas_ventas -> marts.ventas 
# categorias -> raw.categorias # importante 
# codigos_productos -> raw.productos
# historical_data -> raw.tazas_historicas # importante
# usd_mxn_rates -> raw.tazas_extraidas #importante

import pandas as pd

from pathlib import Path
from airflow import DAG
from datetime import timedelta
from common.paths import DATA_DIR
from common.db import create_table, upsert_df
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook


raw_data_path = DATA_DIR/"raw"
conn_str = "dashboard_app_db"
def extract(raw_data_directory:Path)->tuple[pd.DataFrame,pd.DataFrame]:

    categories = pd.read_parquet(raw_data_directory/"categorias.parquet",engine="pyarrow")
    categories = categories.drop(columns=["imagen","slug","fecha"])
    raw_rates = pd.read_csv(raw_data_directory/"historical_data_usd_mxn_2008-12-31_to_2026-01-20.csv",sep=";")
    
    return categories,raw_rates

def transform(categories:pd.DataFrame,raw_rates:pd.DataFrame)->tuple[pd.DataFrame,pd.DataFrame]:

    print(raw_rates.columns)
    raw_rates = raw_rates[["Date","Close"]]
    raw_rates = ( raw_rates .rename(columns={"Date":"date",
                                            "Close":"exchange_rate"})

                            .astype({"exchange_rate":"float"})

                )
    categories = categories.rename(columns={"idCategoria":"categoryId",
                                            "idPadre":"parentId",
                                            "nombre":"category"})
    
    return categories,raw_rates

def load(categories:pd.DataFrame,raw_rates:pd.DataFrame,conn_str):
    hook = PostgresHook(postgres_conn_id=conn_str)
    create_table(hook,"raw","tazas_historicas",{"date"           :"DATE PRIMARY KEY",
                                            "exchange_rate"  :"NUMERIC"})
    print("Poblando tabla de conversiones USD->MXN de moneda limpias...")
    upsert_df(hook,"raw","tazas_historicas",raw_rates,["date"])

    create_table(hook,"raw","categorias",{"categoryId":"Integer PRIMARY KEY",
                                            "parentId"  :"Integer",
                                            "category"  :"VARCHAR"})
    print("Poblando tabla de categorias de productos...")
    upsert_df(hook,"raw","categorias",categories,["categoryId"])



def run_extract(**context):
    extracted_data = extract(raw_data_path)
    context["ti"].xcom_push(key="categories", value=extracted_data[0].to_dict(orient="records"))
    context["ti"].xcom_push(key="raw_rates", value=extracted_data[1].to_dict(orient="records"))

def run_transform(**context):
    categories = pd.DataFrame(context["ti"].xcom_pull(task_ids="extract_historical_data", key="categories"))
    raw_rates  = pd.DataFrame(context["ti"].xcom_pull(task_ids="extract_historical_data", key="raw_rates"))

    transformed_data = transform(categories,raw_rates)
    context["ti"].xcom_push(key="categories", value = transformed_data[0].to_dict(orient="records"))
    context["ti"].xcom_push(key="raw_rates",  value = transformed_data[1].to_dict(orient="records"))


def run_load(**context):
    categories = pd.DataFrame( context["ti"].xcom_pull(task_ids="rename_columns", key="categories"))
    raw_rates  = pd.DataFrame( context["ti"].xcom_pull(task_ids="rename_columns", key="raw_rates"))

    
    
    load(categories,raw_rates,conn_str)
    
    


#  Configuración del DAG
default_args = {
    "owner": "Federico",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}

with DAG(
    dag_id="historical_data_migration",
    default_args=default_args,
    description="Script de migración de datos parquet a tablas SQL",
    schedule=None,  # Manual
    catchup=False,
    tags=["raw"],
) as dag:

    extract_task = PythonOperator(
        task_id="extract_historical_data",
        python_callable=run_extract,
    )

    transform_task = PythonOperator(
        task_id="rename_columns",
        python_callable=run_transform,
    )

    load_task = PythonOperator(
        task_id="load_historic_data",
        python_callable=run_load,
    )

    
    extract_task >> transform_task >> load_task