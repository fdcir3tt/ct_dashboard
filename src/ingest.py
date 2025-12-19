import os
import pandas as pd
import logging
import datetime
from data_loader import load_product_codes,get_query 
from dotenv import load_dotenv
from bson import BSON
from pymongo import MongoClient , UpdateOne

load_dotenv()
today = datetime.datetime.today()
# -----------------------------------------------------------
# -----------------------------------------------------------
id_fields = ["_id","existenciaId","codigo"]

Date = datetime.datetime
Document =  dict[str, any]
Documents = list[Document]

# -----------------------------------------------------------
# -----------------------------------------------------------


# -----------------------------------------------------------
# CONEXIÓN
# -----------------------------------------------------------



def connect_to_DB()-> MongoClient:
    """
    Docstring for connect_to_DB
    
    :return: Cliente de mongoDB
    :rtype: Any
    """
    conn_uri = os.getenv("MONGO_URI")
    mongo_db = os.getenv("MONGO_DB")
    existence_table = os.getenv("EXISTENCE_COLLECTION")
    branches_table = os.getenv("BRANCHES_COLLECTION")

    client = MongoClient(conn_uri)
    db = client[mongo_db]
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
        db = connect_to_DB()

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
    cursor = collection.find(filters, fields)
        
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

    observation = {"timestamp":now,
                   "metaField":{
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

logging.basicConfig(
    filename='mongo_stats.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

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

def main(database,now,get_docs_fn=get_documents,get_costs_fn=get_product_cost_dict,make_obs_fn=make_observation,log_fn=log_collection_size):

     
    if database:
        db = database
    else:
        db = connect_to_DB()
    
    # Extracción de información
    exist_docs = get_docs_fn(db)
    cost_dict = get_costs_fn()

    # Generar observaciones 
    insert_docs = [ make_obs_fn(doc,cost_dict,now) for doc in exist_docs ]
    
    # Ingesta
    hist_table = os.getenv("EXISTENCE_HIST_COLLECTION")
    db[hist_table].insert_many(insert_docs)


    # Loggeo
    num_inserted_docs = len(insert_docs)
    log_fn(db,hist_table,num_inserted_docs)
