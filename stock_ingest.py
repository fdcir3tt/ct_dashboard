import os
import pandas as pd
import logging
import datetime
from data_loader import load_product_codes
from dotenv import load_dotenv
from pymongo import MongoClient 

load_dotenv()

logging.basicConfig(
    filename='mongo_stats.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# -----------------------------------------------------------
# -----------------------------------------------------------

example_date = datetime.date.today()
example_doc = {   "_id":123,
                  "inventory":{"values":[1,2],
                               "date_stored":example_date,
                               "update_dates":[example_date]},
                  "date_stored":example_date }
example_client = MongoClient()

Date = type( example_date )
Document = type( example_doc )
Documents = type ( [example_doc,example_doc] )
Client = type ( example_client)

# -----------------------------------------------------------
# -----------------------------------------------------------


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


def connect_to_DB()-> Client:
    conn_uri = os.getenv("MONGO_URI")
    mongo_db = os.getenv("MONGO_DB")
    existence_table = os.getenv("EXISTENCE_COLLECTION")
    branches_table = os.getenv("BRANCHES_COLLECTION")

    client = MongoClient(conn_uri)
    db = client[mongo_db]

def get_documents() -> tuple( Documents ,Documents ):
    """
    Función que retorna conjunto de documentos extraídos de la colección de existencia
    
    :return: Conjunto de documentos extraídos de la colección de existencia e historial
    :rtype: tuple
    """
    db = connect_to_DB()

    # Tabla de existencia
    existence_table = os.getenv("EXISTENCE_COLLECTION")
    filter_condition = {"almacenes.existencia": {"$gt": 0}}
    fields = {"codigo":1,
            "activo":1,
            "almacenes":1,
            "_id":1}
    
    collection = db[existence_table]
    cursor = collection.find( filter_condition,
                            fields
                            )
    existence_docs = list(cursor)

    # Tabla de historial
    hist_table = os.getenv("EXISTENCE_HIST_COLLECTION")

    return existence_docs,hist_docs

def rename_fields (doc:Document)->Document:

    rename_dict = { "_id":"existenceId",
                    "codigo":"productId",
                    "activo":"active",
                    "almacenes":"inventory",
                    }



def delta_docs(new_doc: Document ,old_doc: Document )-> Document:
    """
    Función que detecta si dos documentos son iguales o diferentes.
    Regresa un documento con solo los campos actualizados.
    """
    delta_doc = []
    for key in new_doc:
        # Si la llave no existe en old_doc o el valor cambió, la agregamos
        if key not in old_doc or new_doc[key] != old_doc[key]:
            delta_doc[key] = new_doc[key]

    return delta_doc

def update_
    today = datetime.date.today()
    for d in docs:
        d["date_stored"] = today

    
    db[hist_table].insert_many(insert_docs)
    db[hist_table].update_many(update_docs)

# -----------------------------------------------------------
# CONEXIÓN
# -----------------------------------------------------------



# -----------------------------------------------------------
# CONSULTA
# -----------------------------------------------------------


exist_docs ,hist_docs = get_documents()

product_codes = load_product_codes()


today = datetime.date.today()
for d in docs:
    d["date_stored"] = today



# -----------------------------------------------------------
# FILTROS
# -----------------------------------------------------------


update_docs =
insert_docs =

# -----------------------------------------------------------
# INGESTA Y ACTUALIZACIÓN DE DOCS
# -----------------------------------------------------------






# -----------------------------------------------------------
# LOGS
# -----------------------------------------------------------


num_inserted_docs = len(insert_docs)
log_collection_size(db,hist_table,num_inserted_docs)