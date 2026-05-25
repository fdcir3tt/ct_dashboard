import pandas as pd

from typing import Any
from common.dates import date
from common.data import load_data
from common.registry import register

save_dict = { "existence_docs":"inventory_docs" ,
                 }
today = date("today")
tag = "historical_existence"
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

    observation = {"fechaRegistro":str(today),
                   "productoReferencia":{
                        "existenciaId":raw_doc["_id"],
                        "codigo":productId
                    },
                   "activo":raw_doc["activo"],
                   "almacenes":branch_inventories,
    
    }

    return observation

@register(tag)
def transform_existence_docs(extracted_data:dict[str,list[dict[str,Any]]],**kwargs)->list[dict[str,Any]]:
    documents = extracted_data.get("existence_docs",[])
    return [make_observation(doc) for doc in documents]

    