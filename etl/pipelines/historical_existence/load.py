import os
import datetime

from bson import ObjectId
from typing import Any
from dotenv import load_dotenv
from common.db import connect_to_mongo_db
from common.paths import ENV_DIR
from common.registry import register


env_path = ENV_DIR /".env"
load_dotenv(env_path)
hist_mongo_uri = os.getenv("TRACE_MONGO_URI")
hist_db_name = os.getenv("TRACE_EXISTENCE_DB_NAME")
trace_existence_collection = os.getenv("TRACE_EXISTENCE_COLLECTION")
batch_size = 500 
table_name="tbl_existenciasHistorial"
load_conditions = {"inventory_docs"   :"stop" ,
                    }
tag = "historical_existence"
@register(tag)
def load_inventory_docs(transformed_data:dict[str,list[dict[str,Any]]],**kwargs):
    documents = transformed_data.get("inventory_docs",[])
    hist_database = connect_to_mongo_db(hist_mongo_uri,hist_db_name) 
    for doc in documents:
        doc["productoReferencia.existenciaId"] = ObjectId(doc.get("productoReferencia.existenciaId"))
        
        doc["fechaRegistro"]= datetime.datetime.fromisoformat(doc.get("fechaRegistro"))
    for i in range(0, len(documents), batch_size):
        chunk = documents[i:i+batch_size]
        hist_database[table_name].insert_many(chunk)


