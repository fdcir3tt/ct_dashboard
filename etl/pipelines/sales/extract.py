import os
import pandas as pd

from typing import Any
from dotenv import load_dotenv

from common.registry import register
from common.db import connect_to_mongo_db,get_documents
from common.dates import date,date_interval
from common.paths import ENV_DIR

from airflow.providers.postgres.hooks.postgres import PostgresHook

env_path = ENV_DIR /".env"
load_dotenv(env_path)

mongo_uri = os.getenv("API_MONGO_URI")
public_API = os.getenv("API_MONGO_DB_NAME")
invoices_collection = os.getenv("INVOICES_COLLECTION")
period_length= 30 # días
extracted_conditions = {"invoice_documents" :"stop",
                        "products_info"     :"stop",
                        "exchange_rates"    :"stop",
                       }
tag = "sales"
@register(tag)
def extract_invoice_documents(period_length:int=period_length,**kwargs)->list[dict[str,Any]]:
    database = connect_to_mongo_db(mongo_uri,public_API)
    today = date("today")
    period = date_interval(today,-period_length)
    consult_info = {"filters":{"precio": {"$gt": 0} ,
                               "fecha":{ "$gte" : period[0],"$lte": period[1] },
                                },
                    "fields":{"_id":0,
                              "articulo":1,
                              "cantidad":1,
                              "precio":1,
                              "total":1,
                              "factura":1,
                              "fecha":1,
                              "almacen":1,
                              "cliente":1,
                              }
                       }          
        
    documents = get_documents(database,invoices_collection,consult_info["filters"],consult_info["fields"])
    print(f"Cantidad de docs extraídos:{len(documents)}")
    
    for doc in documents:
        doc["fecha"]=str(doc.get("fecha"))
    return documents

@register(tag)
def extract_products_info(conn_str:str,**kwargs)->pd.DataFrame:
    hook = PostgresHook(postgres_conn_id=conn_str)
    try:
        products_info = hook.get_pandas_df("SELECT * FROM raw.catalogo_productos")
    except Exception as e:
        print("Tabla 'raw.catalogo_productos' no encontrada, regresando DF vacío")
        products_info = pd.DataFrame()
    return products_info

@register(tag)
def extract_exchange_rates(conn_str:str,**kwargs)->pd.DataFrame:
    hook = PostgresHook(postgres_conn_id=conn_str)
    try:
        exchange_rates = hook.get_pandas_df("SELECT * FROM staging.tazas_clean")
    except Exception as e:
        print("Tabla 'staging.tazas_clean' no encontrada, regresando DF vacío")
        exchange_rates = pd.DataFrame()
    return exchange_rates



