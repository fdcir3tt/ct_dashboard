import pandas as pd

from common.db import upsert_df,create_table
from common.data import load_data,delete_files
from airflow.providers.postgres.hooks.postgres import PostgresHook



def load(data:dict[str,pd.DataFrame],conn_str:str="dashboard_app_db"):
    
    category_df      = data["category_df"]
    client_df        = data["client_df"]
    product_codes_df = data["product_codes_df"]
    branches_df      = data["branches_df"]


    hook   = PostgresHook(postgres_conn_id=conn_str)
    
    
    # Categorías
    print("Creando tabla de categorias de productos...")
    create_table(hook,"raw","categorias",{"categoryId":"Integer PRIMARY KEY",
                                          "parentId"  :"Integer",
                                          "category"  :"VARCHAR"})
    print("Poblando tabla de categorias de productos...")
    upsert_df(hook,"raw","categorias",category_df,["categoryId"])

    
    # Clientes
    print("Creando tabla de clientes...")
    create_table(hook,"raw","clientes",{"clientId":"VARCHAR PRIMARY KEY",
                                        "city"    :"VARCHAR"})
    print("Poblando tabla de clientes...")
    upsert_df(hook,"raw","clientes",client_df,["clientId"])

    
    # Productos
    print("Creando tabla de productos...")
    create_table(hook,"raw","productos",{"productId"   :"VARCHAR PRIMARY KEY",
                                         "categoryId"  :"VARCHAR",
                                         "description" :"TEXT",
                                         "cost"        :"REAL",
                                         "buy_coin"    :"Integer",
                                         "sell_coin"   :"Integer"})
    
    print("Poblando tabla de productos...")
    upsert_df(hook,"raw","productos",product_codes_df,key_columns=["productId"])

    # Almacenes
    create_table(hook,"raw","almacenes",{"storageId"   :"VARCHAR PRIMARY KEY",
                                         "branchId"    :"VARCHAR",
                                         "branch"      :"VARCHAR"})
    
    print("Poblando tabla de almacenes...")
    upsert_df(hook,"raw","almacenes",branches_df,key_columns=["storageId"])

def run_load(**context):
    
    print("Convirtiendo contexto a dataframes...")
    transformed_path_strings = context["ti"].xcom_pull(task_ids="rename_and_merge_columns", key="path_strings")
    transformed_data = load_data(transformed_path_strings)
    
    print("Comenzando carga de datos...")
    load(transformed_data)

    delete_files(transformed_path_strings)