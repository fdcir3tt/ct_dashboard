from airflow import DAG
from datetime import datetime, timedelta

from airflow.operators.python import PythonOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator

from pipelines.currency_rates.extract_rates import run_extract_rates 
from pipelines.currency_rates.extract import run_extract
from pipelines.currency_rates.transform import run_transform
from pipelines.currency_rates.load import run_load

#  Configuración del DAG
default_args = {
    "owner": "Federico",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}

with DAG(
    dag_id="currency_rates_pipeline",
    default_args=default_args,
    description="Pipeline de actualización de tazas de conversión de moneda USD a MXN ",
    schedule="0 13 * * *",  # Diario a las 6am MST -7
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["raw","staging"],
) as dag:

    extract_rates_task = PythonOperator(
        task_id="extract_current_rate",
        python_callable=run_extract_rates,
    )

    extract_task = PythonOperator(
        task_id="extract_past_rates",
        python_callable=run_extract,
    )

    transform_task = PythonOperator(
        task_id="rates_merging",
        python_callable=run_transform,
    )

    load_task = PythonOperator(
        task_id="load_clean_rates",
        python_callable=run_load,
    )

    trigger_sales_dag = TriggerDagRunOperator(
        task_id="trigger_sales_dag",
        trigger_dag_id="sales_pipeline",
    )
    
    extract_rates_task >> extract_task >> transform_task >> load_task >> trigger_sales_dag