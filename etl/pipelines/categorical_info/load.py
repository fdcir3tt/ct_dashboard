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
    create_table(hook,"raw","categorias",{"category_id":"Integer PRIMARY KEY",
                                          "parent_id"  :"Integer",
                                          "category"  :"VARCHAR"})
    print("Poblando tabla de categorias de productos...")
    upsert_df(hook,"raw","categorias",category_df,["category_id"])

    
    # Clientes
    print("Creando tabla de clientes...")
    create_table(hook,"raw","clientes",{"client_id":"VARCHAR PRIMARY KEY",
                                        "city"    :"VARCHAR"})
    print("Poblando tabla de clientes...")
    upsert_df(hook,"raw","clientes",client_df,["client_id"])

    
    # Productos
    print("Creando tabla de productos...")
    create_table(hook,"raw","productos",{"product_id"   :"VARCHAR PRIMARY KEY",
                                         "category_id"  :"Integer",
                                         "description" :"TEXT",
                                         "cost"        :"REAL",
                                         "buy_coin"    :"Integer",
                                         "sell_coin"   :"Integer"},foreign_keys={"category_id":'raw.categorias("category_id")'})
    
    print("Poblando tabla de productos...")
    upsert_df(hook,"raw","productos",product_codes_df,key_columns=["product_id"])

    # Almacenes
    create_table(hook,"raw","almacenes",{"storage_id"   :"VARCHAR PRIMARY KEY",
                                         "branch_id"    :"VARCHAR",
                                         "branch"      :"VARCHAR"})
    
    print("Poblando tabla de almacenes...")
    upsert_df(hook,"raw","almacenes",branches_df,key_columns=["storage_id"])

def run_load(**context):
    
    print("Convirtiendo contexto a dataframes...")
    extracted_path_strings = context["ti"].xcom_pull(task_ids="extract_categories_and_products", key="path_strings")
    transformed_path_strings = context["ti"].xcom_pull(task_ids="rename_and_merge_columns", key="path_strings")
    transformed_data = load_data(transformed_path_strings)
    
    print("Comenzando carga de datos...")
    load(transformed_data)

    delete_files(extracted_path_strings+transformed_path_strings)