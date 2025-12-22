import os
import pandas as pd
import logging
import datetime
from data_loader import load_product_codes,get_query 
from dotenv import load_dotenv
from bson import BSON
from pymongo import MongoClient , UpdateOne


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

log_filename = datetime.datetime.now().strftime("historic_stats_%Y%m%d_%H%M%S.log")
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
# CONEXIÓN
# -----------------------------------------------------------



def connect_to_DB(conn_uri,db_name)-> MongoClient:
    """
    Docstring for connect_to_DB
    
    :return: Cliente de mongoDB
    :rtype: Any
    """

    client = MongoClient(conn_uri,compressors="zstd,snappy,zlib",maxPoolSize=5)
    db = client[db_name]

    return db

# -----------------------------------------------------------
# CONSULTA
# -----------------------------------------------------------


def get_documents(database:None) -> Documents:
    """
    Función que regresa lista de documentos extraídos de la colección de existencia
    
    :return: Conjunto de documentos extraídos de la colección de existencia e historial
    :rtype: tuple
    """
    if database:
        db = database
    else:
        db = connect_to_DB(API_CONN,API_NAME)

    consult_info = {
        "EXISTENCE_COLLECTION":{
            "filters":{"almacenes.existencia": {"$gt": 0}},                                
            "fields":{"codigo":1,"activo":1,"almacenes":1,"_id":1} 
            }          
        }

    
    table = os.getenv("EXISTENCE_COLLECTION")  

    info = consult_info["EXISTENCE_COLLECTION"]
    filters = info["filters"]
    fields = info["fields"]


    collection = db[table]
    cursor = collection.find(filters, projection=fields,batch_size=BATCH_SIZE)
        
    result_docs= list(cursor) 
    return result_docs

def get_product_cost_dict(query_fn=get_query)-> dict :
    """
    Función que consulta el datawarehouse para conseguir los costos de productos y los regresa
    como diccionario.
    
    :return: Regresa un diccionario donde las llaves son el código del producto (productId) y los valores el costo correspondiente
    :rtype: dict
    """
    table = os.getenv("ART_TABLE_NAME")
    art_col = os.getenv("ARTICLE_COLUMN")
    art_cost = os.getenv("ARTICLE_COST")

    query = f""" SELECT {art_col},{art_cost} 
                 FROM {table}
            """
    df = query_fn(query)
    cost_dict = df.set_index(art_col).to_dict(orient="index")
    return dict(zip(df[art_col], df[art_cost]))


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
                   "costo":cost_dictionary[productId],
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

     
    if extract_database:
        extract_db = extract_database
    else:
        extract_db = connect_to_DB(API_CONN,API_NAME)
    
    if insert_database:
        insert_db = insert_database
    else: 
        insert_db = connect_to_DB(HISTORIC_CONN,HIST_NAME)
    
    # Extracción de información
    exist_docs = get_docs_fn(extract_db)
    cost_dict = get_costs_fn()
    
    # Ingesta
    hist_table = os.getenv("EXISTENCE_HIST_COLLECTION")
    insert_docs = []
    
    # Procesamiento por chunks para reducir ancho de banda
    for i in range(0, len(exist_docs), BATCH_SIZE):
        chunk = exist_docs[i:i+BATCH_SIZE]
        docs_to_insert = [make_obs_fn(doc, cost_dict, now) for doc in chunk]
        insert_db[hist_table].insert_many(docs_to_insert)
        insert_docs.extend(docs_to_insert)


    # Loggeo
    num_inserted_docs = len(insert_docs)
    log_fn(insert_db,hist_table,num_inserted_docs)




if __name__ == "__main__":
    main()