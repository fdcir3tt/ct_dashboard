import inspect
import pipelines.inventory.extract as extract
import pipelines.inventory.transform as transform 
import pipelines.inventory.load as load


from datetime import timedelta
from common.data import generate_tmp_path_strings,save_data
from common.data import ETL_pipeline

from airflow import DAG
from airflow.operators.python import PythonOperator


from pipelines.inventory.extract import extracted_conditions,extract_historical_existence_documents as inventory_extract
from pipelines.inventory.transform import save_dict
from pipelines.inventory.load import load_conditions


conn_str = "dashboard_app_db"
inventory_period_length = 2*365 # 2 años
tag = "inventory"
conditions_dict = {"period_length"            :inventory_period_length,
                   "extracted_data_is_empty"  :extracted_conditions,
                   "transformed_data_is_empty":load_conditions}
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
    dag_id="inventory_data_migration",
    default_args=default_args,
    description="Script de migración de datos de inventario de ultimos 5 años",
    schedule=None,  # Manual
    catchup=False,
    tags=["etl","marts"],
) as dag:

    inventory_pipeline = ETL_pipeline(extract_fn_names,transform_fn_names,load_fn_names,conn_str,save_dict,conditions_dict)

    extract_tasks                 = inventory_pipeline.make_extraction_tasks()
    gather_extracted_paths_task   = inventory_pipeline.make_gather_paths_task("gather_extracted_paths")
    transform_tasks               = inventory_pipeline.make_transform_tasks()
    gather_transformed_paths_task = inventory_pipeline.make_gather_paths_task("gather_transformed_paths")
    load_tasks                    = inventory_pipeline.make_load_tasks()
    delete_tmp_files_task         = inventory_pipeline.make_delete_tmp_files_task()

    
    

    
    extract_tasks >> gather_extracted_paths_task >> transform_tasks >> gather_transformed_paths_task >> load_tasks >> delete_tmp_files_task 