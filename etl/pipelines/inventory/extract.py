

import os
import pandas as pd

from pathlib import Path
from typing import Any
from dotenv import load_dotenv
from common.db import connect_to_mongo_db,get_documents
from common.dates import date,date_interval
from common.paths import ENV_DIR
from common.data import save_data,generate_tmp_path_strings
from airflow.providers.postgres.hooks.postgres import PostgresHook

env_path = ENV_DIR /".env"
load_dotenv(env_path)
conn_str = "dashboard_app_db"
hist_mongo_uri = os.getenv("TRACE_MONGO_URI")
hist_db_name = os.getenv("TRACE_EXISTENCE_DB_NAME")
trace_existence_collection = os.getenv("TRACE_EXISTENCE_COLLECTION")

def extract(trace_mongo_uri:str,database_name:str,trace_existence_collection_name:str)->dict[str,list[dict[str,Any]]|pd.DataFrame]:
    extracted_data = {}
    hist_database = connect_to_mongo_db(trace_mongo_uri,database_name)
    
    start_date,end_date =date_interval(date("today"),-30)    
    
     
    consult_info = {"filters":{"fechaRegistro":{"$gte":start_date,
                                                "$lte":end_date}},
                    "fields":{"_id":0,"productoReferencia.existenciaId":0},}          
        
    historical_existence_documents = get_documents(hist_database,trace_existence_collection_name,consult_info["filters"],consult_info["fields"])
    print(f"Cantidad de docs extraídos:{len(historical_existence_documents)}")
    
    for doc in historical_existence_documents:
        doc["fechaRegistro"] = str(doc.get("fechaRegistro"))

    hook = PostgresHook(postgres_conn_id=conn_str)
    try:
        branches = hook.get_pandas_df("SELECT * FROM raw.almacenes")
    except Exception as e:
        print("Tabla 'raw.almacenes' no encontrada, regresando DF vacío")
        branches = pd.DataFrame()
    
    extracted_data["historical_existence_documents"]=historical_existence_documents
    extracted_data["branches"]=branches

    return extracted_data

def run_extract(**context):
    extracted_data = extract(hist_mongo_uri,hist_db_name,trace_existence_collection)
    path_strings = generate_tmp_path_strings(extracted_data)

    save_data(extracted_data,path_strings)
    

    context["ti"].xcom_push(key="path_strings", value= path_strings)
    