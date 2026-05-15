from dotenv import load_dotenv
from datetime import timedelta

from common.paths import DATA_DIR,ENV_DIR
from common.data import generate_tmp_path_strings,save_data

from airflow import DAG
from airflow.operators.python import PythonOperator

from pipelines.sales.extract import extract as sales_extract
from pipelines.sales.transform import run_transform as run_sales_transform
from pipelines.sales.load import run_load as run_sales_load

env_path = ENV_DIR /".env"
load_dotenv(env_path)
raw_data_path = DATA_DIR/"raw"
conn_str = "dashboard_app_db"
sales_period_length = 5*365 # 5 años

def run_sales_extract(**context):
    
    extracted_data = sales_extract(sales_period_length)
    path_strings = generate_tmp_path_strings(extracted_data)
    save_data(extracted_data,path_strings)
    context["ti"].xcom_push(key="sales_path_strings", value=path_strings)
    
#  Configuración del DAG
default_args = {
    "owner": "Federico",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}

with DAG(
    dag_id="sales_data_migration",
    default_args=default_args,
    description="Script de migración de datos de 5 años de ventas",
    schedule=None,  # Manual
    catchup=False,
    tags=["etl"],
) as dag:

    
    extract_sales = PythonOperator(
        task_id="extract_rates_branches_products_and_categories",
        python_callable=run_sales_extract,
    )
   
    transform_sales = PythonOperator(
        task_id="merge_and_normalize_coins",
        python_callable=run_sales_transform,
    )
    

    load_sales = PythonOperator(
        task_id="load_sales",
        python_callable=run_sales_load,
    )
   

    
    extract_sales>> transform_sales>> load_sales 