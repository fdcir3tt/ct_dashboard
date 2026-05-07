import pandas as pd

from common.db import upsert_df,create_table
from common.data import load_data,delete_files
from airflow.providers.postgres.hooks.postgres import PostgresHook



def load(sales_invoices_df:pd.DataFrame,conn_str:str="dashboard_app_db"):
    hook = PostgresHook(postgres_conn_id=conn_str)
    print("Creando tabla de ventas...")
    create_table(hook,"marts","ventas",{"salesId"    :"VARCHAR PRIMARY KEY",
                                        'productId'  :"VARCHAR",
                                        'categoryId'  :"VARCHAR",
                                        'quantity'   :"Integer",
                                        'date'       :"DATE",
                                        'price'      :"REAL",
                                        'total'      :"REAL",
                                        'clientId'   :"VARCHAR",
                                        'folio'      :"VARCHAR",
                                        'sale_storageId'  :"VARCHAR",
                                        'description':"TEXT",
                                        'sale_description':"TEXT",
                                        'cost'       :"REAL",
                                        'storageId'  :"VARCHAR",
                                        'branchId'  :"VARCHAR",
                                        'branch'     :"VARCHAR",
                                        'category'   :"VARCHAR"})
    print("Poblando tabla de ventas...")
    upsert_df(hook,"marts","ventas",sales_invoices_df,["salesId"])


def run_load(**context):
    
    print("Convirtiendo contexto a dataframes...")
    sales_path = context["ti"].xcom_pull(task_ids="merge_and_normalize_coins", key="sales_invoices_path")
    sales_invoices_df = load_data(sales_path)
    print("Comenzando carga de datos...")
    load(sales_invoices_df)
    delete_files(sales_path)