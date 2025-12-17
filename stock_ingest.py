import os
import pandas as pd
import logging
import datetime
from src.data_loader import load_product_codes,get_query 
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
Documents = dict[str, Document]

# -----------------------------------------------------------
# -----------------------------------------------------------



# -----------------------------------------------------------
# LOGS
# -----------------------------------------------------------

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

def get_documents(client:None) -> tuple[ Documents ,Documents ]:
    """
    Función que retorna conjunto de documentos extraídos de la colección de existencia
    
    :return: Conjunto de documentos extraídos de la colección de existencia e historial
    :rtype: tuple
    """
    if client:
        db = client
    else:
        db = connect_to_DB()

    consult_info = {"EXISTENCE_COLLECTION":{"filters":{"almacenes.existencia": {"$gt": 0},
                                            "fields":{"codigo":1,"activo":1,"almacenes":1,"_id":1} }},

                    "EXISTENCE_HIST_COLLECTION":{"filters": {},
                                                 "fields": {} }   }
    
    result_docs = []

    for table_name, info in consult_info.items():
        table = os.getenv(table_name)  

        filters = info.get("filters", {})
        fields = info.get("fields", {})

        collection = db[table]
        cursor = collection.find(filters, fields)
        

        doc_dict = {doc["_id"]: doc for doc in cursor}
        if table_name=="EXISTENCE_HIST_COLLECTION":
            doc_dict = {doc["existenceId"]: doc for doc in cursor}

        result_docs.append(doc_dict)

 
    return result_docs[0],result_docs[1]

def get_product_cost_dict()-> dict :
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
    df = get_query(query)
    cost_dict = df.set_index(art_col).to_dict(orient="index")
    return cost_dict


# -----------------------------------------------------------
# FILTROS
# -----------------------------------------------------------

def delta_docs(new_doc: Document ,old_doc: Document )-> Document:
    """
    Función que detecta si dos documentos son iguales o diferentes.
    Regresa un documento con solo los campos actualizados.
    """
    delta_doc = {}
    for key in new_doc:
        # Si la llave no existe en old_doc o el valor cambió, la agregamos
        if ( key not in old_doc ) or ( new_doc[key] != old_doc[key] ):
            delta_doc[key] = new_doc[key]

    return delta_doc

def update_doc(ref_doc:Document,update_doc:Document)-> Document:
    """
    Función que recibe el documento de referencia y de actualización para generar un nuevo documento
    actualizado.

    :param ref_doc: Documento de referencia, el documento que se quiere actualizar.
    :type ref_doc: Document
    :param update_doc: Documento con información de actualización.
    :type update_doc: Document
    :return: Documento referencia con información de actualización añadida
    :rtype: Document
    """
    updated_doc = ref_doc.copy()
    for field,value in update_doc:
        updated_doc[field].append({"valor":value,"fechaRegistro":today})
        updated_doc["fechaUpdate"] = today
    
    return update_doc

def compare_doc_size(ref_doc:Document,update_doc:Document)->tuple[float,bool]:
    """
    Función que recibe el documento de referencia y de actualización y comparar sus tamaños combinados en MB con un umbral para
    lograr saber si el documento de referencia puede llegar a actualizarse correctamente sin problema 
    a la colección de historiales. 
    
    :param ref_doc: Documento de referencia, el documento que se quiere actualizar.
    :type ref_doc: Document
    :param update_doc: Documento con información de actualización.
    :type update_doc: Document
    :return: Resultados de comparación, el primer elemento es la diferencia de tamaños en MB, y el segundo un booleano representando si se puede actualizar el documento base o no
    :rtype: tuple[float, bool]
    """
    threshold =  16 * (1024**2) # bytes
    ref_bytes = BSON.encode ( ref_doc )
    ref_size = len(ref_bytes)

    updated_bytes = BSON.encode ( update_doc(ref_doc,update_doc) )
    updated_size = len(updated_bytes)
    

    diff_size =  updated_size - ref_size 

    diff_size_MB = round ( diff_size / 1024**2 , 2 )
    can_update = threshold > updated_size 
    return diff_size_MB, can_update


# -----------------------------------------------------------
# INGESTA Y ACTUALIZACIÓN DE DOCS
# -----------------------------------------------------------

def update_table(updates:Documents,client:None):
    """
    Función que recibe los documentos que se quieren actualizar y los documentos que contienen solo la
    información actualizada. Actualiza solo los cambios a la tabla de historial. 
    
    :param docs: Documentos referencia que se actualizaran
    :type docs: Documents
    :param update_info: Documentos que contienen información actualizada 
    :type update_docs: Documents


    """
    if client:
        db = client
    else:
        db = connect_to_DB()

    today = datetime.date.today()
    update_ops = []
    
    for u in updates:
        information = {}
        for field,value in u.items():
            if field in id_fields:
                continue
            if isinstance(value, list):
                information[field] = { "$each":value }
            else:
                information[field] = { "$each":[value] }

        update_ops.append(
        UpdateOne(
            {"_id": u["_id"],"codigo": u["codigo"]}, # Filtros
            {
                "$push": information,
                "$currentDate": {"fechaUpdate": True}
            }
        )
    )
        
    hist_table = os.getenv("EXISTENCE_HIST_COLLECTION")
    db[hist_table].bulk_write(update_ops, ordered=False)

    print(f"{len(updates)} documentos actualizados correctamente!")  





# -----------------------------------------------------------
# MAIN PIPELINE
# -----------------------------------------------------------

def main(client:None):

    if client:
        db = client
    else:
        db = connect_to_DB()

    exist_docs ,hist_docs = get_documents()
    product_codes = load_product_codes()
    cost_dict = get_product_cost_dict()


    update_docs = []
    insert_docs = []
    for existenceId,e in exist_docs.items():   
        h = hist_docs[existenceId]
        productId = e["codigo"]

        # Comparación de información
        old_doc = {
                "codigo":h["codigo"],
                "costo":h["costo"][-1]["valor"],
                "activo":h["activo"][-1]["valor"],
                "almacen":h["almacen"][-1]["valor"] }
        
        new_doc = {
                "codigo":productId,
                "costo":cost_dict[productId],
                "activo":e["activo"],
                "almacen":e["almacen"] }
        
        updates = delta_docs(new_doc,old_doc)
        
        # Comparación de tamaño

        size_diff,is_update = compare_doc_size(ref_doc=h,update_doc=updates)
        
        if is_update:
            update_docs.append(updates)
        else:
            insert_docs.append(updates)


    hist_table = os.getenv("EXISTENCE_HIST_COLLECTION")
    update_table(update_docs)
    db[hist_table].insert_many(insert_docs)


    num_inserted_docs = len(insert_docs)
    log_collection_size(db,hist_table,num_inserted_docs)