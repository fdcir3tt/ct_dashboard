import os
import pymongo

from bson import ObjectId
from typing import Any
from dotenv import load_dotenv
from common.db import connect_to_mongo_db
from common.paths import ENV_DIR
from common.data import load_data,delete_files

env_path = ENV_DIR /".env"
load_dotenv(env_path)
hist_mongo_uri = os.getenv("TRACE_MONGO_URI")
hist_db_name = os.getenv("TRACE_EXISTENCE_DB_NAME")
trace_existence_collection = os.getenv("TRACE_EXISTENCE_COLLECTION")
batch_size = 500 
table_name="tbl_existenciasHistorial"

def load(documents:list[dict[str,Any]],database:pymongo.database.Database,collection_name:str,batch_size:int): 
    for doc in documents:
        doc["productoReferencia.existenciaId"] = ObjectId(doc.get("productoReferencia.existenciaId"))
    for i in range(0, len(documents), batch_size):
        chunk = documents[i:i+batch_size]
        database[collection_name].insert_many(chunk)

def run_load(**context):
    existences_docs_path = context["ti"].xcom_pull(task_ids="extract_existence_docs", key="product_existences_path")

    insert_documents_path = context["ti"].xcom_pull(task_ids="make_new_docs", key="docs_to_insert_path")
    insert_documents = load_data(insert_documents_path)
    
    hist_database = connect_to_mongo_db(hist_mongo_uri,hist_db_name)
    load(insert_documents,hist_database,table_name,batch_size)
    
    delete_files([insert_documents_path,existences_docs_path])
