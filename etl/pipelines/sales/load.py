import pandas as pd

from common.db import upsert_df,create_table
from common.data import load_data,delete_files
from airflow.providers.postgres.hooks.postgres import PostgresHook



def load(sales_invoices_df:pd.DataFrame,conn_str:str="dashboard_app_db"):
    hook = PostgresHook(postgres_conn_id=conn_str)
    print("Creando tabla de ventas...")
    create_table(hook,"etl","ventas",{  "sales_id"         :"VARCHAR PRIMARY KEY",
                                        'product_id'       :"VARCHAR",
                                        'description'      :"TEXT",
                                        'quantity'         :"Integer",
                                        'date'             :"DATE",
                                        'total'            :"REAL",
                                        'price'            :"REAL",
                                        'cost'             :"REAL",
                                        'client_id'        :"VARCHAR",
                                        'folio'            :"VARCHAR",
                                        'sale_storage_id'  :"VARCHAR",},foreign_keys={"sale_storage_id":"raw.catalogo_almacenes(storage_id)",
                                                                                     "product_id":"raw.catalogo_productos(product_id)"})
    print("Poblando tabla de ventas...")
    upsert_df(hook,"etl","ventas",sales_invoices_df,["sales_id"])


def run_load(**context):
    
    print("Convirtiendo contexto a dataframes...")
    path_strings = context["ti"].xcom_pull(task_ids="extract_rates_branches_products_and_categories", key="sales_path_strings")
    sales_path = context["ti"].xcom_pull(task_ids="merge_and_normalize_coins", key="sales_invoices_path")
    
    sales_invoices_df = load_data(sales_path)
    print("Comenzando carga de datos...")
    load(sales_invoices_df)
    delete_files([sales_path]+path_strings)