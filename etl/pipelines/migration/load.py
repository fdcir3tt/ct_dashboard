import pandas as pd
from common.db import create_table, upsert_df
from common.registry import register

from airflow.providers.postgres.hooks.postgres import PostgresHook


load_conditions = {"categories_df"          :"skip" ,
                   "raw_rates_df"           :"stop" ,
                   "product_codes_df"       :"skip",
                   "extracted_rates_df"     :"stop" }
tag = "migration"

@register(tag)
def load_categories_df(conn_str:str,transformed_data:dict[str,pd.DataFrame]):
    categories_df = transformed_data["categories_df"]
    hook = PostgresHook(postgres_conn_id=conn_str)
    print("Creando tabla de categorias de productos...")
    create_table(hook,"raw","catalogo_categorias",{"category_id":"Integer PRIMARY KEY",
                                                   "parent_id"  :"Integer",
                                                   "category"   :"VARCHAR"})
    print("Poblando tabla de categorias de productos...")
    upsert_df(hook,"raw","catalogo_categorias",categories_df,["category_id"])

@register(tag)
def load_raw_rates_df(conn_str:str,transformed_data:dict[str,pd.DataFrame]):
    raw_rates_df = transformed_data["raw_rates_df"]
    hook = PostgresHook(postgres_conn_id=conn_str)
    create_table(hook,"raw","tazas_historicas",{"date"           :"DATE PRIMARY KEY",
                                                "exchange_rate"  :"NUMERIC"})
    print("Poblando tabla de conversiones USD->MXN de moneda limpias...")
    upsert_df(hook,"raw","tazas_historicas",raw_rates_df,["date"])

@register(tag)
def load_product_codes_df(conn_str:str,transformed_data:dict[str,pd.DataFrame]):
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
def load_extracted_rates_df(conn_str:str,transformed_data:dict[str,pd.DataFrame]):
    extracted_rates_df = transformed_data["extracted_rates_df"]
    hook = PostgresHook(postgres_conn_id=conn_str)
    create_table(hook,"raw","tazas_extraidas",{"date"         :"DATE PRIMARY KEY",
                                               "exchange_rate":"NUMERIC",
                                               "fallback"     :"VARCHAR"})
    print("Poblando tabla de tazas extraídas...")
    upsert_df(hook,"raw","tazas_extraidas",extracted_rates_df,["date"])
