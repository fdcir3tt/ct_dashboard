import inspect
import pipelines.migration.extract as extract
import pipelines.migration.transform as transform 
import pipelines.migration.load as load

from datetime import timedelta
from common.data import ETL_pipeline
from pipelines.migration.extract import extracted_conditions 
from pipelines.migration.transform import save_dict
from pipelines.migration.load import load_conditions 

from airflow import DAG
from airflow.operators.trigger_dagrun import TriggerDagRunOperator


conn_str = "dashboard_app_db"
conditions_dict = {"extracted_data_is_empty"  :extracted_conditions,
                   "transformed_data_is_empty":load_conditions}
tag = "migration"

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



#  Configuración del DAG
default_args = {
    "owner": "Federico",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}

with DAG(
    dag_id="product_category_and_coin_rates_backup",
    default_args=default_args,
    description="Script de migración de datos parquet a tablas SQL",
    schedule=None,  # Manual
    catchup=False,
    tags=["raw"],
) as dag:

    categories_migration_pipeline = ETL_pipeline(extract_fn_names,transform_fn_names,load_fn_names,conn_str,save_dict,conditions_dict)

    extract_tasks                 = categories_migration_pipeline.make_extraction_tasks()
    gather_extracted_paths_task   = categories_migration_pipeline.make_gather_paths_task("gather_extracted_paths")
    transform_tasks               = categories_migration_pipeline.make_transform_tasks()
    gather_transformed_paths_task = categories_migration_pipeline.make_gather_paths_task("gather_transformed_paths")
    load_tasks                    = categories_migration_pipeline.make_load_tasks()
    delete_tmp_files_task         = categories_migration_pipeline.make_delete_tmp_files_task()
    
    
    trigger_categorical_info_dag = TriggerDagRunOperator(
        task_id="trigger_categorical_info_dag",
        trigger_dag_id="categorical_info",
    )

    trigger_currency_dag = TriggerDagRunOperator(
        task_id="trigger_currency_rates_dag",
        trigger_dag_id="currency_rates",
    )
    
    trigger_shapefile_dag = TriggerDagRunOperator(
        task_id="trigger_shapefile_dag",
        trigger_dag_id="mexico_shapefile_extraction",
    )

    

    trigger_shapefile_dag >> extract_tasks >> gather_extracted_paths_task >> transform_tasks >> gather_transformed_paths_task >> load_tasks >> delete_tmp_files_task >> [trigger_categorical_info_dag,trigger_currency_dag]

