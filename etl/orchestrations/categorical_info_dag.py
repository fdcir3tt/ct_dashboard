from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
from pipelines.categorical_info.extract import run_extract
from pipelines.categorical_info.transform import run_transform
from pipelines.categorical_info.load import run_load

#  Configuración del DAG
default_args = {
    "owner": "Federico",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}

with DAG(
    dag_id="categorical_info_pipeline",
    default_args=default_args,
    description="Pipeline información categórica ",
    schedule_interval="0 6 1 */2 *",  # Bimensual a las 6am
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["raw"],
) as dag:

   
    extract_task = PythonOperator(
        task_id="extract_categories_and_products",
        python_callable=run_extract,
    )

    transform_task = PythonOperator(
        task_id="rename_and_merge_columns",
        python_callable=run_transform,
    )

    load_task = PythonOperator(
        task_id="load_categories_and_products",
        python_callable=run_load,
    )

    
    extract_task >> transform_task >> load_task