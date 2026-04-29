import os
import psycopg
import pandas as pd

from dotenv import load_dotenv
from common.db import upsert_df,create_table
from airflow.providers.postgres.hooks.postgres import PostgresHook



def load(category_df:pd.DataFrame,client_df:pd.DataFrame,product_codes_df:pd.DataFrame,conn_str:str="dashboard_app_db"):

    hook = PostgresHook(postgres_conn_id=conn_str)
    
    print("Creando tabla de categorias de productos...")
    # Categorías
    create_table(hook,"raw","categorias",{"productId":"VARCHAR PRIMARY KEY",
                                        "category" :"VARCHAR"})
    print("Poblando tabla de categorias de productos...")
    upsert_df(hook,"raw","categorias",category_df,["productId"])

    print("Creando tabla de clientes...")
    # Clientes
    create_table(hook,"raw","clientes",{"clientId":"VARCHAR PRIMARY KEY",
                                  "city"    :"VARCHAR"})
    print("Poblando tabla de clientes...")
    upsert_df(hook,"raw","clientes",client_df,["clientId"])

    print("Creando tabla de productos...")
    # Productos
    create_table(hook,"raw","productos",{"productId"   :"VARCHAR PRIMARY KEY",
                                       "description" :"TEXT",
                                       "cost"        :"REAL",
                                       "buy_coin"    :"Integer",
                                       "sell_coin"   :"Integer"})
    
    print("Poblando tabla de productos...")
    upsert_df(hook,"raw","productos",product_codes_df,key_columns=["productId"])

def run_load(**context):
    print("Convirtiendo contexto a dataframes...")
    category_df = pd.DataFrame(context["ti"].xcom_pull(task_ids="transform", key="category_df"))
    client_df = pd.DataFrame(context["ti"].xcom_pull(task_ids="transform", key="client_df"))
    product_codes_df = pd.DataFrame(context["ti"].xcom_pull(task_ids="transform", key="product_codes_df"))
    print("Comenzando carga de datos...")
    load(category_df,client_df,product_codes_df)