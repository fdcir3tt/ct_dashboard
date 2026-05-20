import pandas as pd

from common.db import upsert_df,create_table
from common.registry import register

from airflow.providers.postgres.hooks.postgres import PostgresHook

load_conditions = {"categories_df"   :"skip" ,
                   "clients_df"      :"stop" ,
                   "product_codes_df":"skip",
                   "branches_df"     :"stop" }

tag = "categorical_info"

@register(tag)
def load_categories_df(conn_str:str,transformed_data:dict[str,pd.DataFrame])->None:
    category_df = transformed_data["categories_df"]
    hook = PostgresHook(postgres_conn_id=conn_str)
    print("Creando tabla de categorias de productos...")
    create_table(hook,"raw","catalogo_categorias",{"category_id":"Integer PRIMARY KEY",
                                                   "parent_id"  :"Integer",
                                                   "category"   :"VARCHAR"})
    print("Poblando tabla de categorias de productos...")
    upsert_df(hook,"raw","catalogo_categorias",category_df,["category_id"])
@register(tag)
def load_clients_df(conn_str:str,transformed_data:dict[str,pd.DataFrame])->None:
    clients_df = transformed_data["clients_df"]
    hook = PostgresHook(postgres_conn_id=conn_str)
    print("Creando tabla de clientes...")
    create_table(hook,"raw","catalogo_clientes",{"client_id":"VARCHAR PRIMARY KEY",
                                                 "city"    :"VARCHAR"})
    print("Poblando tabla de clientes...")
    upsert_df(hook,"raw","catalogo_clientes",clients_df,["client_id"])

@register(tag)
def load_product_codes_df(conn_str:str,transformed_data:dict[str,pd.DataFrame])->None:
    product_codes_df = transformed_data["product_codes_df"]
    hook = PostgresHook(postgres_conn_id=conn_str)
    print("Creando tabla de productos...")
    create_table(hook,"raw","catalogo_productos",{"product_id"  :"VARCHAR PRIMARY KEY",
                                                  "category_id" :"Integer",
                                                  "description" :"TEXT",
                                                  "cost"        :"REAL",
                                                  "buy_coin"    :"Integer",
                                                  "sell_coin"   :"Integer"},foreign_keys={"category_id":'raw.catalogo_categorias("category_id")'})
            
    print("Poblando tabla de productos...")
    upsert_df(hook,"raw","catalogo_productos",product_codes_df,key_columns=["product_id"])

@register(tag)
def load_branches_df(conn_str:str,transformed_data:dict[str,pd.DataFrame])->None:
    branches_df = transformed_data["branches_df"]
    hook = PostgresHook(postgres_conn_id=conn_str)
    create_table(hook,"raw","catalogo_almacenes",{"storage_id"   :"VARCHAR PRIMARY KEY",
                                                  "branch_id"    :"VARCHAR",
                                                  "branch"       :"VARCHAR",
                                                  "state"        :"VARCHAR"})
    print("Poblando tabla de almacenes...")
    upsert_df(hook,"raw","catalogo_almacenes",branches_df,key_columns=["storage_id"])
    

