import inspect
import pipelines.sales.extract as extract
import pipelines.sales.transform as transform 
import pipelines.sales.load as load

from airflow import DAG
from datetime import timedelta

from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook

from common.data import ETL_pipeline

from pipelines.sales.extract import extracted_conditions
from pipelines.sales.transform import save_dict
from pipelines.sales.load import load_conditions

conn_str = "dashboard_app_db"
conditions_dict = {"extracted_data_is_empty"  :extracted_conditions,
                   "transformed_data_is_empty":load_conditions}
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
    dag_id="sales_pipeline",
    default_args=default_args,
    description="Pipeline de ventas de productos físicos ",
    schedule= None,  
    catchup=False,
    tags=["etl","marts"],
) as dag:
    
    sales_pipeline = ETL_pipeline(extract_fn_names,transform_fn_names,load_fn_names,conn_str,save_dict,conditions_dict)

    extract_tasks                 = sales_pipeline.make_extraction_tasks()
    gather_extracted_paths_task   = sales_pipeline.make_gather_paths_task("gather_extracted_paths")
    transform_tasks               = sales_pipeline.make_transform_tasks()
    gather_transformed_paths_task = sales_pipeline.make_gather_paths_task("gather_transformed_paths")
    load_tasks                    = sales_pipeline.make_load_tasks()
    delete_tmp_files_task         = sales_pipeline.make_delete_tmp_files_task()
    
    create_sales_info_table =PostgresOperator(
        task_id = "create_sales_info_table" ,
        postgres_conn_id ="dashboard_app_db",
        sql = """CREATE TABLE IF NOT EXISTS marts.informacion_ventas(
                                            sales_id        INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                                            product_id      VARCHAR,
                                            quantity        BIGINT,
                                            date            DATE,
                                            price           REAL,
                                            total           REAL,
                                            client_id       VARCHAR,
                                            folio           VARCHAR,
                                            description     TEXT,
                                            cost            REAL,
                                            sale_storage_id VARCHAR,
                                            branch_id       VARCHAR,
                                            branch          VARCHAR,
                                            category        VARCHAR
                                            )"""
    )

    insert_data = PostgresOperator(
        task_id = "insert_sales_info" ,
        postgres_conn_id ="dashboard_app_db",
        sql = """INSERT INTO marts.informacion_ventas (
                                                        product_id,
                                                        quantity,
                                                        date,
                                                        price,
                                                        total,
                                                        client_id,
                                                        folio,
                                                        description,
                                                        cost,
                                                        sale_storage_id,
                                                        branch_id,
                                                        branch,
                                                        category
                                                    )
                 SELECT             ve.product_id,
                                    ve.quantity,
                                    ve.date,
                                    ve.price,
                                    ve.total,
                                    ve.client_id,
                                    ve.folio,
                                    ve.description,
                                    ve.cost,
                                    ve.sale_storage_id,
                                    ca.branch_id,
                                    ca.branch,
                                    cc.category
                FROM etl.ventas AS ve
                LEFT JOIN raw.catalogo_productos cp ON cp.product_id = ve.product_id
                LEFT JOIN raw.catalogo_categorias cc ON cp.category_id=cc.category_id
                LEFT JOIN raw.catalogo_almacenes ca ON ve.sale_storage_id = ca.storage_id;
                             """
    )


    
    extract_tasks >> gather_extracted_paths_task >> transform_tasks >> gather_transformed_paths_task >> load_tasks >> delete_tmp_files_task >> create_sales_info_table >> insert_data