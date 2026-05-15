import pandas as pd

from typing import Callable
from common.db import upsert_df,create_table
from common.data import load_data,delete_files
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.exceptions import AirflowSkipException

def load_categories_df(hook:PostgresHook,category_df:pd.DataFrame)->None:
    print("Creando tabla de categorias de productos...")
    create_table(hook,"raw","catalogo_categorias",{"category_id":"Integer PRIMARY KEY",
                                                   "parent_id"  :"Integer",
                                                   "category"   :"VARCHAR"})
    print("Poblando tabla de categorias de productos...")
    upsert_df(hook,"raw","catalogo_categorias",category_df,["category_id"])

def load_clients_df(hook:PostgresHook,clients_df:pd.DataFrame)->None:
    print("Creando tabla de clientes...")
    create_table(hook,"raw","catalogo_clientes",{"client_id":"VARCHAR PRIMARY KEY",
                                                 "city"    :"VARCHAR"})
    print("Poblando tabla de clientes...")
    upsert_df(hook,"raw","catalogo_clientes",clients_df,["client_id"])

def load_product_codes_df(hook:PostgresHook,product_codes_df:pd.DataFrame)->None:
    print("Creando tabla de productos...")
    create_table(hook,"raw","catalogo_productos",{"product_id"   :"VARCHAR PRIMARY KEY",
                                                  "category_id"  :"Integer",
                                                  "description" :"TEXT",
                                                  "cost"        :"REAL",
                                                  "buy_coin"    :"Integer",
                                                  "sell_coin"   :"Integer"},foreign_keys={"category_id":'raw.catalogo_categorias("category_id")'})
            
    print("Poblando tabla de productos...")
    upsert_df(hook,"raw","catalogo_productos",product_codes_df,key_columns=["product_id"])

def load_branches_df(hook:PostgresHook,branches_df:pd.DataFrame)->None:
    create_table(hook,"raw","catalogo_almacenes",{"storage_id"   :"VARCHAR PRIMARY KEY",
                                                  "branch_id"    :"VARCHAR",
                                                  "branch"       :"VARCHAR",
                                                  "state"        :"VARCHAR"})
    print("Poblando tabla de almacenes...")
    upsert_df(hook,"raw","catalogo_almacenes",branches_df,key_columns=["storage_id"])
    

def run_load(hook:PostgresHook,load_fn:Callable,**context):
    
    extracted_path_strings = context["ti"].xcom_pull(task_ids="gather_transformed_paths", key="path_strings")
    transformed_data = load_data(extracted_path_strings)
    
    transformed_data_name = load_fn.__name__.split("load_")[1]
    not_transformed = transformed_data_name not in transformed_data.keys()
    if not_transformed:
            raise AirflowSkipException(f"Skipping task,missing transformed data:{transformed_data_name.replace("_"," ")} ")

    transformed_df = transformed_data[transformed_data_name]
    
    load_fn(hook,transformed_df)

def delete_temp_files(**context):
    extracted_path_strings   = context["ti"].xcom_pull(task_ids="gather_extracted_paths", key="path_strings")
    transformed_path_strings = context["ti"].xcom_pull(task_ids="gather_transformed_paths", key="path_strings")
    delete_files(extracted_path_strings+transformed_path_strings)