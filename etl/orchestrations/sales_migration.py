
import inspect
import pipelines.sales.extract as extract
import pipelines.sales.transform as transform 
import pipelines.sales.load as load

from airflow import DAG
from datetime import timedelta

from common.data import ETL_pipeline
from pipelines.sales.extract import extracted_conditions
from pipelines.sales.transform import save_dict
from pipelines.sales.load import load_conditions



conn_str = "dashboard_app_db"
sales_period_length = 5*365 # 5 años
conditions_dict = { "period_length"            : sales_period_length,
                    "extracted_data_is_empty"  :extracted_conditions,
                   "transformed_data_is_empty" :load_conditions}
tag = "sales"

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
    dag_id="sales_data_migration",
    default_args=default_args,
    description="Script de migración de datos de 5 años de ventas",
    schedule=None,  # Manual
    catchup=False,
    tags=["etl"],
) as dag:
    sales_pipeline = ETL_pipeline(extract_fn_names,transform_fn_names,load_fn_names,conn_str,save_dict,conditions_dict)

    extract_tasks                 = sales_pipeline.make_extraction_tasks()
    gather_extracted_paths_task   = sales_pipeline.make_gather_paths_task("gather_extracted_paths")
    transform_tasks               = sales_pipeline.make_transform_tasks()
    gather_transformed_paths_task = sales_pipeline.make_gather_paths_task("gather_transformed_paths")
    load_tasks                    = sales_pipeline.make_load_tasks()
    delete_tmp_files_task         = sales_pipeline.make_delete_tmp_files_task()
    
   

    
    extract_tasks >> gather_extracted_paths_task >> transform_tasks >> gather_transformed_paths_task >> load_tasks >> delete_tmp_files_task