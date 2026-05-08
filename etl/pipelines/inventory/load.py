import pandas as pd

from common.db import upsert_df,create_table
from common.data import load_data,delete_files
from airflow.providers.postgres.hooks.postgres import PostgresHook



def load(inventory:pd.DataFrame,conn_str:str="dashboard_app_db"):

    hook = PostgresHook(postgres_conn_id=conn_str)
    print("Creando tabla de inventario...")

    # Categorías
    create_table(hook,"etl","inventory",{"existenceId":"VARCHAR PRIMARY KEY",
                                         "productId"  :"VARCHAR",
                                         "date"       :"DATE",
                                         "stock"      :"Integer",
                                         "storageId"  :"VARCHAR"})
    print("Poblando tabla de inventario...")
    upsert_df(hook,"etl","inventory",inventory,["existenceId"])

    

def run_load(**context):
    
    print("Convirtiendo contexto a dataframes...")
    inventory_path = context["ti"].xcom_pull(task_ids="explode_and_rearrange_data", key="inventory_path")
    inventory = load_data(inventory_path)
    
    print("Comenzando carga de datos...")
    load(inventory)
    
    delete_files(inventory_path)