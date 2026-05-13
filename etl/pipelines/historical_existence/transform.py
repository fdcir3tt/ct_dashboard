import pandas as pd

from typing import Any
from common.dates import date
from common.data import save_data,load_data,delete_files

today = date("today")

def make_observation(raw_doc:dict[str,Any])->dict[str,Any] :
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

    observation = {"fechaRegistro":today,
                   "productoReferencia":{
                        "existenciaId":raw_doc["_id"],
                        "codigo":productId
                    },
                   "activo":raw_doc["activo"],
                   "almacenes":branch_inventories,
    
    }

    return observation

def transform(documents:list[dict[str,Any]])->list[dict[str,Any]]:
    return [make_observation(doc) for doc in documents]

def run_transform(**context):
    
    existences_docs_path = context["ti"].xcom_pull(task_ids="extract_existence_docs", key="product_existences_path")
    existences_docs = load_data(existences_docs_path)
    transformed_data = transform(existences_docs)

    context["ti"].xcom_push(key="docs_to_insert_path", value=transformed_data)
    