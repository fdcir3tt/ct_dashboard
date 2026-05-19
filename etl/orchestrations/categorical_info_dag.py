import inspect
import pipelines.categorical_info.extract as extract
import pipelines.categorical_info.transform as transform 
import pipelines.categorical_info.load as load

from airflow import DAG
from common.data import ETL_pipeline

from datetime import datetime, timedelta
from pipelines.categorical_info.extract import extracted_conditions
from pipelines.categorical_info.transform import save_dict
from pipelines.categorical_info.load import load_conditions

conn_str = "dashboard_app_db"
conditions_dict = {"extracted_data_is_empty"  :extracted_conditions,
                   "transformed_data_is_empty":load_conditions}
tag = "categorical_info"

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
    dag_id="categorical_info",
    default_args=default_args,
    description="Pipeline información categórica ",
    schedule_interval="0 13 1 */2 *",  # Bimensual a las 6am
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["raw"],
) as dag:
    
    categorical_info_pipeline = ETL_pipeline(extract_fn_names,transform_fn_names,load_fn_names,conn_str,save_dict,conditions_dict)

    extract_tasks                 = categorical_info_pipeline.make_extraction_tasks()
    gather_extracted_paths_task   = categorical_info_pipeline.make_gather_paths_task("gather_extracted_paths")
    transform_tasks               = categorical_info_pipeline.make_transform_tasks()
    gather_transformed_paths_task = categorical_info_pipeline.make_gather_paths_task("gather_transformed_paths")
    load_tasks                    = categorical_info_pipeline.make_load_tasks()
    delete_tmp_files_task         = categorical_info_pipeline.make_delete_tmp_files_task()
    
    extract_tasks >> gather_extracted_paths_task >> transform_tasks >> gather_transformed_paths_task >> load_tasks >> delete_tmp_files_task