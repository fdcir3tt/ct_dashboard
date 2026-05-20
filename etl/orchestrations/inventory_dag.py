import inspect
import pipelines.inventory.extract as extract
import pipelines.inventory.transform as transform 
import pipelines.inventory.load as load

from datetime import datetime, timedelta
from common.data import ETL_pipeline
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.utils.trigger_rule import TriggerRule

from pipelines.inventory.extract import extracted_conditions
from pipelines.inventory.transform import save_dict
from pipelines.inventory.load import load_conditions

conn_str      = "dashboard_app_db"
tag = "inventory"
conditions_dict = {"extracted_data_is_empty"  :extracted_conditions,
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
    dag_id="inventory_pipeline",
    default_args=default_args,
    description="Pipeline de tabla de inventario de productos físicos",
    schedule_interval="0 13 * * *",  # Diario a las 6am MST -7
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["etl"],
) as dag:

    inventory_pipeline = ETL_pipeline(extract_fn_names,transform_fn_names,load_fn_names,conn_str,save_dict,conditions_dict)

    extract_tasks                 = inventory_pipeline.make_extraction_tasks()
    gather_extracted_paths_task   = inventory_pipeline.make_gather_paths_task("gather_extracted_paths")
    transform_tasks               = inventory_pipeline.make_transform_tasks()
    gather_transformed_paths_task = inventory_pipeline.make_gather_paths_task("gather_transformed_paths")
    load_tasks                    = inventory_pipeline.make_load_tasks()
    delete_tmp_files_task         = inventory_pipeline.make_delete_tmp_files_task()

    create_inventory_info_table = PostgresOperator(
        task_id = "create_inventory_info_table" ,
        postgres_conn_id ="dashboard_app_db",
        trigger_rule=TriggerRule.ALL_DONE,
        sql = """CREATE TABLE IF NOT EXISTS marts.informacion_inventario(
                                            inventory_id INTEGER PRIMARY KEY,
                                            product_id   VARCHAR,
                                            date         DATE,
                                            stock        BIGINT,
                                            storage_id   VARCHAR,
                                            branch       VARCHAR,
                                            category     VARCHAR
                                            )"""
    )
    insert_data = PostgresOperator(
        task_id = "insert_inventory_info" ,
        postgres_conn_id ="dashboard_app_db",
        sql = """
                WITH source_data AS (
                                    SELECT DISTINCT ON (inv.inventory_id)
                                            inv.product_id,
                                            inv.date,
                                            inv.stock,
                                            inv.storage_id,
                                            alm.branch,
                                            ca.category
                                        FROM etl.inventario inv
                                        JOIN raw.catalogo_almacenes alm      ON inv.storage_id=alm.storage_id
                                        JOIN raw.catalogo_productos prod     ON inv.product_id=prod.product_id
                                        LEFT JOIN raw.catalogo_categorias ca ON prod.category_id=ca.category_id
                                )
        
                INSERT INTO marts.informacion_inventario(inventory_id,
                                                          product_id ,
                                                          date ,
                                                          stock,
                                                          storage_id ,
                                                          branch ,
                                                          category )
                SELECT *
                FROM source_data
                ON CONFLICT (inventory_id)
                DO UPDATE SET 
                    product_id      = EXCLUDED.product_id,
                    date            = EXCLUDED.date,
                    stock           = EXCLUDED.stock,
                    storage_id      = EXCLUDED.storage_id,
                    branch          = EXCLUDED.branch,
                    category        = EXCLUDED.category;
                ;
                                            """
    )
    
    extract_tasks >> gather_extracted_paths_task >> transform_tasks >> gather_transformed_paths_task >> load_tasks >> delete_tmp_files_task >> create_inventory_info_table >> insert_data