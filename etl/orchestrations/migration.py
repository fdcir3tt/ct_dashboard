# Tables:

# branches    -> raw.almacenes
# conversion_usd_mxn  -> staging.tazas_clean
# facturas_ventas -> marts.ventas 
# categorias -> raw.categorias # importante 
# codigos_productos -> raw.productos
# historical_data -> raw.tazas_historicas # importante
# usd_mxn_rates -> raw.tazas_extraidas #importante
import os
import pandas as pd

from dotenv import load_dotenv
from pathlib import Path
from datetime import timedelta

from common.paths import DATA_DIR,ENV_DIR
from common.data import generate_tmp_path_strings,save_data
from common.db import create_table, upsert_df

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook

from pipelines.inventory.extract import extract as inventory_extract
from pipelines.inventory.transform import run_transform as run_inventory_transform
from pipelines.inventory.load import run_load as run_inventory_load

from pipelines.sales.extract import extract as sales_extract
from pipelines.sales.transform import run_transform as run_sales_transform
from pipelines.sales.load import run_load as run_sales_load

env_path = ENV_DIR /".env"
load_dotenv(env_path)
raw_data_path = DATA_DIR/"raw"
conn_str = "dashboard_app_db"
sales_period_length = 5*365 # 5 años
inventory_period_length = 5*365 # 5 años
hist_mongo_uri = os.getenv("TRACE_MONGO_URI")
hist_db_name = os.getenv("TRACE_EXISTENCE_DB_NAME")
trace_existence_collection = os.getenv("TRACE_EXISTENCE_COLLECTION")


def extract(raw_data_directory:Path)->tuple[pd.DataFrame,pd.DataFrame]:

    categories = pd.read_parquet(raw_data_directory/"categorias.parquet",engine="pyarrow")
    categories = categories.drop(columns=["imagen","slug","fecha"])
    raw_rates = pd.read_csv(raw_data_directory/"historical_data_usd_mxn_2008-12-31_to_2026-01-20.csv",sep=";")
    extracted_rates = pd.read_parquet(raw_data_directory/"usd_mxn_rates.parquet",engine="pyarrow")
    extracted_rates["date"]=extracted_rates.index
    extracted_rates["date"] = extracted_rates["date"].dt.date
    return categories,raw_rates,extracted_rates

def transform(categories:pd.DataFrame,raw_rates:pd.DataFrame,extracted_rates:pd.DataFrame)->tuple[pd.DataFrame,pd.DataFrame]:

    
    raw_rates = raw_rates[["Date","Close"]]
    raw_rates = ( raw_rates .rename(columns={"Date":"date",
                                            "Close":"exchange_rate"})

                            .astype({"exchange_rate":"float"})

                )
    categories = categories.rename(columns={"idCategoria":"category_id",
                                            "idPadre":"parent_id",
                                            "nombre":"category"})
    extracted_rates["fallback"]=""
    return categories,raw_rates,extracted_rates

def load(categories:pd.DataFrame,raw_rates:pd.DataFrame,extracted_rates:pd.DataFrame,conn_str):
    hook = PostgresHook(postgres_conn_id=conn_str)
    create_table(hook,"raw","tazas_historicas",{"date"           :"DATE PRIMARY KEY",
                                            "exchange_rate"  :"NUMERIC"})
    print("Poblando tabla de conversiones USD->MXN de moneda limpias...")
    upsert_df(hook,"raw","tazas_historicas",raw_rates,["date"])

    create_table(hook,"raw","catalogo_categorias",{"category_id":"Integer PRIMARY KEY",
                                            "parent_id"  :"Integer",
                                            "category"  :"VARCHAR"})
    print("Poblando tabla de categorias de productos...")
    upsert_df(hook,"raw","catalogo_categorias",categories,["category_id"])

    create_table(hook,"raw","tazas_extraidas",{"date"         :"DATE PRIMARY KEY",
                                               "exchange_rate":"NUMERIC",
                                               "fallback"     :"VARCHAR"})
    upsert_df(hook,"raw","tazas_extraidas",extracted_rates,["date"])


def run_extract(**context):
    extracted_data = extract(raw_data_path)
    context["ti"].xcom_push(key="categories", value=extracted_data[0].to_dict(orient="records"))
    context["ti"].xcom_push(key="raw_rates", value=extracted_data[1].to_dict(orient="records"))
    context["ti"].xcom_push(key="extracted_rates", value=extracted_data[2].to_dict(orient="records"))

def run_transform(**context):
    categories = pd.DataFrame(context["ti"].xcom_pull(task_ids="extract_historical_data", key="categories"))
    raw_rates  = pd.DataFrame(context["ti"].xcom_pull(task_ids="extract_historical_data", key="raw_rates"))
    extracted_rates  = pd.DataFrame(context["ti"].xcom_pull(task_ids="extract_historical_data", key="extracted_rates"))

    transformed_data = transform(categories,raw_rates,extracted_rates)
    context["ti"].xcom_push(key="categories", value = transformed_data[0].to_dict(orient="records"))
    context["ti"].xcom_push(key="raw_rates",  value = transformed_data[1].to_dict(orient="records"))
    context["ti"].xcom_push(key="extracted_rates",  value = transformed_data[2].to_dict(orient="records"))


def run_load(**context):
    categories = pd.DataFrame( context["ti"].xcom_pull(task_ids="rename_columns", key="categories"))
    raw_rates  = pd.DataFrame( context["ti"].xcom_pull(task_ids="rename_columns", key="raw_rates"))
    extracted_rates  = pd.DataFrame( context["ti"].xcom_pull(task_ids="rename_columns", key="extracted_rates"))

    print(extracted_rates.head())
    load(categories,raw_rates,extracted_rates,conn_str)
    
    
def run_sales_extract(**context):
    
    extracted_data = sales_extract(sales_period_length)
    path_strings = generate_tmp_path_strings(extracted_data)
    save_data(extracted_data,path_strings)
    context["ti"].xcom_push(key="sales_path_strings", value=path_strings)
    
def run_inventory_extract(**context):
    extracted_data = inventory_extract(hist_mongo_uri,hist_db_name,trace_existence_collection,inventory_period_length)
    path_strings = generate_tmp_path_strings(extracted_data)

    save_data(extracted_data,path_strings)
    context["ti"].xcom_push(key="inv_path_strings", value= path_strings)

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
    tags=["raw","etl"],
) as dag:

    extract_task = PythonOperator(
        task_id="extract_historical_data",
        python_callable=run_extract,
    )
    extract_sales = PythonOperator(
        task_id="extract_rates_branches_products_and_categories",
        python_callable=run_sales_extract,
    )
    extract_inventory = PythonOperator(
        task_id="extract_historical_data_and_branches",
        python_callable=run_inventory_extract,
    )

    transform_task = PythonOperator(
        task_id="rename_columns",
        python_callable=run_transform,
    )

    transform_sales = PythonOperator(
        task_id="merge_and_normalize_coins",
        python_callable=run_sales_transform,
    )
    transform_inventory= PythonOperator(
        task_id="explode_and_rearrange_data",
        python_callable=run_inventory_transform,
    )

    load_task = PythonOperator(
        task_id="load_historic_data",
        python_callable=run_load,
    )
    load_sales = PythonOperator(
        task_id="load_sales",
        python_callable=run_sales_load,
    )
    load_inventory = PythonOperator(
        task_id="load_inventory",
        python_callable=run_inventory_load,
    )

    
    extract_task>>[extract_sales,extract_inventory] >> transform_task>>[transform_sales,transform_inventory] >> load_task >>[load_sales,load_inventory]