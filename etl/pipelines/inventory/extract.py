import os
import pandas as pd

from typing import Any
from dotenv import load_dotenv

from common.db import connect_to_mongo_db,get_documents
from common.registry import register
from common.dates import date,date_interval
from common.paths import ENV_DIR

from airflow.providers.postgres.hooks.postgres import PostgresHook

env_path = ENV_DIR /".env"
load_dotenv(env_path)
conn_str = "dashboard_app_db"
hist_mongo_uri = os.getenv("TRACE_MONGO_URI")
hist_db_name = os.getenv("TRACE_EXISTENCE_DB_NAME")
trace_existence_collection = os.getenv("TRACE_EXISTENCE_COLLECTION")
extracted_conditions = {"historical_existence_documents" :"stop",
                        "branches"                       :"stop",
                       }
tag="inventory"
@register(tag)
def extract_historical_existence_documents(trace_mongo_uri:str=hist_mongo_uri,database_name:str=hist_db_name,trace_existence_collection_name:str=trace_existence_collection,period_length:int=3,**kwargs)->list[dict[str,Any]]:
    hist_database = connect_to_mongo_db(trace_mongo_uri,database_name)
    
    start_date,end_date =date_interval(date("today"),-period_length)    
    
     
    consult_info = {"filters":{"fechaRegistro":{"$gte":start_date,
                                                "$lte":end_date}},
                    "fields":{"_id":0,"productoReferencia.existenciaId":0},}          
        
    historical_existence_documents = get_documents(hist_database,trace_existence_collection_name,consult_info["filters"],consult_info["fields"])
    print(f"Cantidad de docs extraídos:{len(historical_existence_documents)}")
    for doc in historical_existence_documents:
        doc["fechaRegistro"] = str(doc.get("fechaRegistro"))
    return historical_existence_documents

@register(tag)
def extract_branches(conn_str:str,**kwargs):
    hook = PostgresHook(postgres_conn_id=conn_str)
    try:
        branches = hook.get_pandas_df("SELECT * FROM raw.catalogo_almacenes")
    except Exception as e:
        print("Tabla 'raw.catalogo_almacenes' no encontrada, regresando DF vacío")
        branches = pd.DataFrame()
    return branches


    