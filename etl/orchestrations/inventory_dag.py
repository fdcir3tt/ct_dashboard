from airflow import DAG
from datetime import datetime, timedelta
from airflow.operators.python import PythonOperator
from pipelines.inventory.extract import run_extract
from pipelines.inventory.transform import run_transform
from pipelines.inventory.load import run_load

#  Configuración del DAG
default_args = {
    "owner": "Federico",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}

with DAG(
    dag_id="inventory_pipeline",
    default_args=default_args,
    description="Pipeline de tabla de inventario de productos físicos",
    schedule_interval="0 13 * * *",  # Diario a las 6am MST -7
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["etl"],
) as dag:

    extract_task = PythonOperator(
        task_id="extract_historical_data_and_branches",
        python_callable=run_extract,
    )

    transform_task = PythonOperator(
        task_id="explode_and_rearrange_data",
        python_callable=run_transform,
    )

    load_task = PythonOperator(
        task_id="load_inventory",
        python_callable=run_load,
    )

    
    extract_task >> transform_task >> load_task