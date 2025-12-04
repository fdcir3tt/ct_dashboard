import os
import pandas as pd
import logging
import datetime
from dotenv import load_dotenv
from pymongo import MongoClient 

load_dotenv()

logging.basicConfig(
    filename='mongo_stats.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def log_collection_size(db, collection_name:str,num_inserted_docs:int=None):
    stats = db.command("collStats", collection_name)
    if num_inserted_docs:
        logging.info(
            f"Stats de '{collection_name}': "
            f"num_inserted_docs={num_inserted_docs}"
            f"num_docs={stats.get("count")} docs,"
            f"size={stats.get('size', 0)} bytes, "
            f"storageSize={stats.get('storageSize', 0)} bytes, "
            f"totalSize={stats.get('totalSize', 0)} bytes"
        )
    else:
        logging.info(
            f"Stats de '{collection_name}': "
            f"num_docs={stats.get("count")}"
            f"size={stats.get('size', 0)} bytes, "
            f"storageSize={stats.get('storageSize', 0)} bytes, "
            f"totalSize={stats.get('totalSize', 0)} bytes"
        )

def different_docs(docs:list[str])->list[str]:
    return docs

# -----------------------------------------------------------
# CONEXIÓN
# -----------------------------------------------------------

conn_uri = os.getenv("MONGO_URI")
mongo_db = os.getenv("MONGO_DB")
existence_table = os.getenv("EXISTENCE_COLLECTION")
branches_table = os.getenv("BRANCHES_COLLECTION")

client = MongoClient(conn_uri)
db = client[mongo_db]

# -----------------------------------------------------------
# CONSULTA
# -----------------------------------------------------------


filter_condition = {"almacenes.existencia": {"$gt": 0}}
fields = {"codigo":1,"activo":1,"almacenes":1,"_id":1}

collection = db[existence_table]
cursor = collection.find( filter_condition,
                          fields
                          )
docs = list(cursor)

today = datetime.date.today()
for d in docs:
    d["date_stored"] = today

# -----------------------------------------------------------
# INGESTA
# -----------------------------------------------------------

insert_docs = different_docs(docs)
hist_table = os.getenv("EXISTENCE_HIST_COLLECTION")
db[hist_table].insert_many(insert_docs)


# -----------------------------------------------------------
# LOGS
# -----------------------------------------------------------

num_inserted_docs = len(insert_docs)
log_collection_size(db,hist_table,num_inserted_docs)