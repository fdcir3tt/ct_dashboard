import inspect
import pipelines.historical_existence.extract as extract
import pipelines.historical_existence.transform as transform 
import pipelines.historical_existence.load as load

from airflow import DAG
from datetime import datetime, timedelta
from common.data import ETL_pipeline,load_data,data_is_empty

from airflow.operators.python import PythonOperator
from airflow.operators.python import ShortCircuitOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator

from pipelines.historical_existence.extract import extracted_conditions
from pipelines.historical_existence.transform import save_dict
from pipelines.historical_existence.load import load_conditions

conn_str = ""
conditions_dict = {"extracted_data_is_empty"  :extracted_conditions,
                   "transformed_data_is_empty":load_conditions}
tag = "historical_existence"

extract_fns   = inspect.getmembers(extract  , inspect.isfunction)
transform_fns = inspect.getmembers(transform, inspect.isfunction)
load_fns      = inspect.getmembers(load     , inspect.isfunction)


extract_fn_names   = [f"{tag}.{name}" for name,_ in extract_fns   if name.startswith("extract") ] 
transform_fn_names = [f"{tag}.{name}" for name,_ in transform_fns if name.startswith("transform") ] 
load_fn_names      = [f"{tag}.{name}" for name,_ in load_fns      if name.startswith("load") and (name!="load_dotenv") ] 



#  Configuración del DAG
default_args = {
    "owner": "Federico",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}

def should_continue(**context):
    extracted_docs_path = context["ti"].xcom_pull(
        task_ids="gather_extracted_paths",
        key="path_strings"
    ) or []

    if not extracted_docs_path:
        return False

    file_path = extracted_docs_path[0]
    extracted_docs = load_data(file_path)
    print(extracted_docs[0])
    return not data_is_empty(extracted_docs)


with DAG(
    dag_id="historical_existence_pipeline",
    default_args=default_args,
    description="Pipeline de ingesta de existencias a tabla de historial de existencias ",
    schedule ="0 13 * * *",  # Diario a las 6am MST -7
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["external"],
) as dag:

    
    historical_existence_pipeline = ETL_pipeline(extract_fn_names,transform_fn_names,load_fn_names,conn_str,save_dict,conditions_dict)

    extract_tasks                 = historical_existence_pipeline.make_extraction_tasks()
    gather_extracted_paths_task   = historical_existence_pipeline.make_gather_paths_task("gather_extracted_paths")
    transform_tasks               = historical_existence_pipeline.make_transform_tasks()
    gather_transformed_paths_task = historical_existence_pipeline.make_gather_paths_task("gather_transformed_paths")
    load_tasks                    = historical_existence_pipeline.make_load_tasks()
    delete_tmp_files_task         = historical_existence_pipeline.make_delete_tmp_files_task()
    
    
    check = ShortCircuitOperator(
        task_id="check_if_collection_up_to_date",
        python_callable=should_continue,
    )

    trigger_inventory_dag = TriggerDagRunOperator(
        task_id="trigger_inventory_dag",
        trigger_dag_id="inventory_pipeline",
    )
    
    extract_tasks >> gather_extracted_paths_task >> check >> transform_tasks >> gather_transformed_paths_task >> load_tasks >> delete_tmp_files_task >> trigger_inventory_dag