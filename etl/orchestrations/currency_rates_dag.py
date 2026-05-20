import inspect
import pipelines.currency_rates.extract as extract
import pipelines.currency_rates.transform as transform 
import pipelines.currency_rates.load as load
from airflow import DAG
from datetime import datetime, timedelta

from airflow.operators.python import PythonOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from common.data import ETL_pipeline

from pipelines.currency_rates.extract_rates import run_extract_rates 
from pipelines.currency_rates.extract import extracted_conditions
from pipelines.currency_rates.transform import save_dict
from pipelines.currency_rates.load import load_conditions

conn_str = "dashboard_app_db"
conditions_dict = {"extracted_data_is_empty"  :extracted_conditions,
                   "transformed_data_is_empty":load_conditions}
tag = "currency_rates"

extract_fns   = inspect.getmembers(extract  , inspect.isfunction)
transform_fns = inspect.getmembers(transform, inspect.isfunction)
load_fns      = inspect.getmembers(load     , inspect.isfunction)


extract_fn_names   = [f"{tag}.{name}" for name,_ in extract_fns   if name.startswith("extract") ] 
transform_fn_names = [f"{tag}.{name}" for name,_ in transform_fns if name.startswith("transform") ] 
load_fn_names      = [f"{tag}.{name}" for name,_ in load_fns      if name.startswith("load") ] 




#  Configuración del DAG
default_args = {
    "owner": "Federico",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}

with DAG(
    dag_id="currency_rates",
    default_args=default_args,
    description="Pipeline de actualización de tazas de conversión de moneda USD a MXN ",
    schedule="0 13 * * *",  # Diario a las 6am MST -7
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["raw","staging"],
) as dag:

    extract_rates_task = PythonOperator(
        task_id="get_API_rate",
        python_callable=run_extract_rates
    )
    
    currency_rates_pipeline = ETL_pipeline(extract_fn_names,transform_fn_names,load_fn_names,conn_str,save_dict,conditions_dict)

    extract_tasks                 = currency_rates_pipeline.make_extraction_tasks()
    gather_extracted_paths_task   = currency_rates_pipeline.make_gather_paths_task("gather_extracted_paths")
    transform_tasks               = currency_rates_pipeline.make_transform_tasks()
    gather_transformed_paths_task = currency_rates_pipeline.make_gather_paths_task("gather_transformed_paths")
    load_tasks                    = currency_rates_pipeline.make_load_tasks()
    delete_tmp_files_task         = currency_rates_pipeline.make_delete_tmp_files_task()

    trigger_sales_dag = TriggerDagRunOperator(
        task_id="trigger_sales_dag",
        trigger_dag_id="sales_pipeline",
    )
    
    extract_rates_task >> extract_tasks >> gather_extracted_paths_task >> transform_tasks >> gather_transformed_paths_task >> load_tasks >> delete_tmp_files_task >> trigger_sales_dag