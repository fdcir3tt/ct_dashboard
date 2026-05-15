# Tables:

# branches    -> raw.almacenes
# conversion_usd_mxn  -> staging.tazas_clean
# facturas_ventas -> marts.ventas 
# categorias -> raw.categorias # importante 
# codigos_productos -> raw.productos
# historical_data -> raw.tazas_historicas # importante
# usd_mxn_rates -> raw.tazas_extraidas #importante
import os

from dotenv import load_dotenv
from datetime import timedelta

from common.paths import ENV_DIR
from common.data import generate_tmp_path_strings,save_data


from airflow import DAG
from airflow.operators.python import PythonOperator


from pipelines.inventory.extract import extract as inventory_extract
from pipelines.inventory.transform import run_transform as run_inventory_transform
from pipelines.inventory.load import run_load as run_inventory_load



env_path = ENV_DIR /".env"
load_dotenv(env_path)
conn_str = "dashboard_app_db"
inventory_period_length = 5*365 # 5 años
hist_mongo_uri = os.getenv("TRACE_MONGO_URI")
hist_db_name = os.getenv("TRACE_EXISTENCE_DB_NAME")
trace_existence_collection = os.getenv("TRACE_EXISTENCE_COLLECTION")

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
    dag_id="inventory_data_migration",
    default_args=default_args,
    description="Script de migración de datos de inventario de ultimos 5 años",
    schedule=None,  # Manual
    catchup=False,
    tags=["etl","marts"],
) as dag:

    extract_inventory = PythonOperator(
        task_id="extract_historical_data_and_branches",
        python_callable=run_inventory_extract,
    )

    
    transform_inventory= PythonOperator(
        task_id="explode_and_rearrange_data",
        python_callable=run_inventory_transform,
    )

   
    
    load_inventory = PythonOperator(
        task_id="load_inventory",
        python_callable=run_inventory_load,
    )

    
    extract_inventory >>transform_inventory>>load_inventory