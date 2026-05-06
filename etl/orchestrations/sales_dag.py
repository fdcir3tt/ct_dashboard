from airflow import DAG
from datetime import timedelta

from airflow.operators.python import PythonOperator

from pipelines.sales.extract import run_extract
from pipelines.sales.transform import run_transform
from pipelines.sales.load import run_load

#  Configuración del DAG
default_args = {
    "owner": "Federico",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}

with DAG(
    dag_id="sales_pipeline",
    default_args=default_args,
    description="Pipeline de ventas de productos físicos ",
    schedule= None,  
    catchup=False,
    tags=["marts"],
) as dag:
    
    extract_task = PythonOperator(
        task_id="extract_rates_branches_products_and_categories",
        python_callable=run_extract,
    )

    transform_task = PythonOperator(
        task_id="merge_and_normalize_coins",
        python_callable=run_transform,
    )

    load_task = PythonOperator(
        task_id="load_sales",
        python_callable=run_load,
    )

    
    extract_task >> transform_task >> load_task