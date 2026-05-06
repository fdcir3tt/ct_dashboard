import os
import pandas as pd

from typing import Any
from dotenv import load_dotenv
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
conn_str = "dashboard_app_db"

def extract()->list[dict[str,Any]]:
    # invoices
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
                              "descripcion":1}
                       }          
        
    documents = get_documents(database,invoices_collection,consult_info["filters"],consult_info["fields"])
    print(f"Cantidad de docs extraídos:{len(documents)}")

    # product_codes
    hook = PostgresHook(postgres_conn_id=conn_str)
    try:
        products_info = hook.get_pandas_df("SELECT * FROM raw.productos")
    except Exception as e:
        print("Tabla 'raw.productos' no encontrada, regresando DF vacío")
        products_info = pd.DataFrame()
    
    # exchange_rates
    try:
        exchange_rates = hook.get_pandas_df("SELECT * FROM staging.tazas_clean")
    except Exception as e:
        print("Tabla 'staging.tazas_clean' no encontrada, regresando DF vacío")
        exchange_rates = pd.DataFrame()

    # branches
    try:
        branches = hook.get_pandas_df("SELECT * FROM raw.almacenes")
    except Exception as e:
        print("Tabla 'raw.almacenes' no encontrada, regresando DF vacío")
        branches = pd.DataFrame()

    # categories
    try:
        categories = hook.get_pandas_df("SELECT * FROM raw.categorias")
    except Exception as e:
        print("Tabla 'raw.categorias' no encontrada, regresando DF vacío")
        categories = pd.DataFrame()
    return documents,products_info,exchange_rates,branches,categories


def run_extract(**context):
    extracted_data = extract()
    context["ti"].xcom_push(key="extracted_invoice_documents", value=extracted_data[0])
    context["ti"].xcom_push(key="products_info", value=extracted_data[1].to_dict(orient="records"))
    context["ti"].xcom_push(key="exchange_rates", value=extracted_data[2].to_dict(orient="records"))
    context["ti"].xcom_push(key="branches", value=extracted_data[3].to_dict(orient="records"))
    context["ti"].xcom_push(key="categories", value=extracted_data[4].to_dict(orient="records"))
    
    