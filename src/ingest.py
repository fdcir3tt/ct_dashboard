import os
import pandas as pd
import logging
import datetime
from src.data_loader import *
from dotenv import load_dotenv
from bson import BSON



# -----------------------------------------------------------
# SETUP 
# -----------------------------------------------------------
load_dotenv()

BATCH_SIZE = 500
HISTORIC_CONN = os.getenv("HIST_MONGO_URI")
HIST_NAME= os.getenv("HIST_MONGO_DB")
API_CONN = os.getenv("API_MONGO_URI")
API_NAME = os.getenv("API_MONGO_DB")
LOG_DIR = "log"

os.makedirs(LOG_DIR, exist_ok=True)

log_filename = "historic_stats.log"
log_path = os.path.join(LOG_DIR, log_filename)

logging.basicConfig(
    filename=log_path,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

today = datetime.datetime.today()

id_fields = ["_id","existenciaId","codigo"]

Date = datetime.datetime
Document =  dict[str, any]
Documents = list[Document]


# -----------------------------------------------------------
# INGESTA
# -----------------------------------------------------------

def make_observation(raw_doc:Document,cost_dictionary:dict,now:datetime.datetime)->Document :
    """
    Función que recibe información de existencia y se queda con solo la información relevante al final
    """
    productId = raw_doc["codigo"]
    inventory = raw_doc["almacenes"]

    branch_inventories = {}
    for item in inventory:
        branch = item["almacen"]
        stock = item["existencia"]
        if stock > 0 :
            branch_inventories[branch]=stock

    observation = {"fechaRegistro":now,
                   "productoReferencia":{
                        "existenciaId":raw_doc["_id"],
                        "codigo":productId
                    },
                   "activo":raw_doc["activo"],
                   "costo":cost_dictionary.get(productId, 0),
                   "almacenes":branch_inventories,
    
    }

    return observation

# -----------------------------------------------------------
# LOGS
# -----------------------------------------------------------


def log_collection_size(db, collection_name, logger=logging.info, num_inserted_docs=None):
    stats = db.command("collStats", collection_name)

    msg = (
        f"Stats '{collection_name}': "
        f"count={stats.get('count')} "
        f"size={stats.get('size', 0)} "
        f"storage={stats.get('storageSize', 0)} "
        f"total={stats.get('totalSize', 0)}"
    )

    if num_inserted_docs is not None:
        msg = f"inserted={num_inserted_docs} " + msg

    logger(msg)




# -----------------------------------------------------------
# MAIN PIPELINE
# -----------------------------------------------------------

def main(extract_database=None,insert_database=None,now=datetime.datetime.now(),get_docs_fn=get_documents,get_costs_fn=get_product_cost_dict,make_obs_fn=make_observation,log_fn=log_collection_size):

     
    if extract_database is not None:
        extract_db = extract_database
    else:
        extract_db = connect_to_DB(API_CONN,API_NAME)
    
    if insert_database is not None:
        insert_db = insert_database
    else: 
        insert_db = connect_to_DB(HISTORIC_CONN,HIST_NAME)
    
    # Extracción de información

    consult_info = {
        "EXISTENCE_COLLECTION":{
            "filters":{"almacenes.existencia": {"$gt": 0}},                                
            "fields":{"codigo":1,"activo":1,"almacenes":1,"_id":1} 
            }          
        }
    collection = os.getenv("EXISTENCE_COLLECTION")  

    info = consult_info["EXISTENCE_COLLECTION"]
    filters = info["filters"]
    projection = info["fields"]

    exist_docs = get_docs_fn(extract_db,collection,filters,projection)
    cost_dict = get_costs_fn()
    
    # Ingesta
    hist_table = os.getenv("EXISTENCE_HIST_COLLECTION")
    
    
    # Procesamiento por chunks para reducir ancho de banda
    num_inserted_docs = 0
    for i in range(0, len(exist_docs), BATCH_SIZE):
        chunk = exist_docs[i:i+BATCH_SIZE]
        docs_to_insert = [make_obs_fn(doc, cost_dict, now) for doc in chunk]
        insert_db[hist_table].insert_many(docs_to_insert)
        
        num_inserted_docs += len(docs_to_insert)

    # Loggeo
    
    log_fn(db=insert_db,collection_name=hist_table,num_inserted_docs=num_inserted_docs)




if __name__ == "__main__":
    main()