import pandas as pd

from common.db import upsert_df,create_table
from common.data import load_data,delete_files
from airflow.providers.postgres.hooks.postgres import PostgresHook



def load(inventory:pd.DataFrame,conn_str:str="dashboard_app_db"):

    hook = PostgresHook(postgres_conn_id=conn_str)
    print("Creando tabla de inventario...")

    # Categorías
    create_table(hook,"etl","inventario",{"existence_id":"VARCHAR PRIMARY KEY",
                                         "product_id"   :"VARCHAR",
                                         "date"         :"DATE",
                                         "stock"        :"BIGINT",
                                         "storage_id"   :"VARCHAR"},foreign_keys={
                                                                                  "storage_id":'raw.catalogo_almacenes(storage_id)'})
    print("Poblando tabla de inventario...")
    upsert_df(hook,"etl","inventario",inventory,["existence_id"])

    

def run_load(**context):
    path_strings = context["ti"].xcom_pull(task_ids="extract_historical_data_and_branches", key="inv_path_strings")

    print("Convirtiendo contexto a dataframes...")
    inventory_path = context["ti"].xcom_pull(task_ids="explode_and_rearrange_data", key="inventory_path")
    inventory = load_data(inventory_path)
    
    print("Comenzando carga de datos...")
    load(inventory)
    
    delete_files([inventory_path]+path_strings)