from airflow import DAG
from datetime import datetime, timedelta

from airflow.operators.python import PythonOperator
from airflow.operators.python import ShortCircuitOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator

from pipelines.historical_existence.extract import run_extract
from pipelines.historical_existence.transform import run_transform
from pipelines.historical_existence.load import run_load

#  Configuración del DAG
default_args = {
    "owner": "Federico",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}

def should_continue(**context):
    up_to_date = context["ti"].xcom_pull(task_ids="extract",key="up_to_date")

    
    return up_to_date  


with DAG(
    dag_id="historical_existence_pipeline",
    default_args=default_args,
    description="Pipeline de ingesta de existencias a tabla de historial de existencias ",
    schedule ="0 13 * * *",  # Diario a las 6am MST -7
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["external"],
) as dag:

    

    extract_task = PythonOperator(
        task_id="extract_existence_docs",
        python_callable=run_extract,
    )
    check = ShortCircuitOperator(
        task_id="check_if_collection_up_to_date",
        python_callable=should_continue,
    )
    transform_task = PythonOperator(
        task_id="make_new_docs",
        python_callable=run_transform,
    )

    load_task = PythonOperator(
        task_id="load_docs",
        python_callable=run_load,
    )

    trigger_inventory_dag = TriggerDagRunOperator(
        task_id="trigger_inventory_dag",
        trigger_dag_id="inventory_pipeline",
    )
    extract_task >> check >> transform_task >> load_task >> trigger_inventory_dag
