import pytest
import pandas as pd
import os
import shutil
import re
import datetime
import mongomock
import random
from datetime import datetime, timedelta, timezone
from bson import ObjectId
from dotenv import load_dotenv
from  stock_ingest import *
from deepdiff import DeepDiff

load_dotenv()



# -----------------------------------------------
# BASE DE DATOS FALSA
# -----------------------------------------------

mongo_db = os.getenv("MONGO_DB")
existence_name = os.getenv("EXISTENCE_COLLECTION") 
historic_name = os.getenv("EXISTENCE_HIST_COLLECTION") 


client = mongomock.MongoClient()
db = client[mongo_db]
existence_table = db[existence_name]
historic_table = db[historic_name]

fixed_beginning = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
fixed_today = datetime(2025, 16, 12, 11, 27, 0, tzinfo=timezone.utc)
random.seed(42)


def random_date(start:datetime.datetime, end:datetime.datetime, seed =None)->datetime.datetime:
    rng = random.Random(seed)
    delta = end - start
    int_delta = delta.total_seconds()
    random_second = rng.randint(0, int(delta))
    return start + timedelta(seconds=random_second)




e_docs = [ { "_id":ObjectId(f"64f1a2b3c4d5e6f70123450{i}"),
             "codigo":f"PROD-0{i}",
             "activo":random.choice([True, False]),
             "fechaRegistro":fixed_beginning,
             "listaPrecios":{ f"precio{k}":random.uniform(50,60) for k in range(1,11)},
             "existencia":{"pedido":random.randint(0,54*160),"asignado":random.randint(0,54*160)},
             "almacenes":[ { "almacen":f"{j}A","existencia":random.randint(10*i,100+10*i) } for j in range(54) ],
             "codigoSAT":2000+i,
             "updatedExistencia":random_date(fixed_beginning,fixed_today,seed=42),
             "updateExistencia":random_date(fixed_beginning,fixed_today,seed=69) } for i in range(1,6)]

existence_table.insert_many(e_docs)



# -----------------------------------------------
# SIMULACIÓN DE ACTUALIZACIONES 
# -----------------------------------------------

rngs=[random.Random(i) for i in range(10)]
update_dates = sorted( [random_date(fixed_beginning,fixed_today,seed=j) for j in range(5)] )
updates = [ {ObjectId(f"64f1a2b3c4d5e6f70123450{i}"):
           {"_id":ObjectId(f"507f1f77bcf86cd79943901{i}"),
             "codigo":f"PROD-0{i}",
             "activo": rngs[i+j].choice([True, False]) ,
             "costo": rngs[i+j].uniform(35,47), 
             "almacenes":[ { f"{ rngs[i+j].randint(0,53) }A":rngs[i+j].randint(10,100) } for _ in range(10) ],
             
              } for i in range(1,6)}  for j in range(5)]

# Tabla inicial
h_dict = {  ObjectId(f"64f1a2b3c4d5e6f70123450{i}"):
            {  "_id":ObjectId(f"64f1a2b3c4d5e6f70123450{i}"),
                "existenciaId":ObjectId(f"64f1a2b3c4d5e6f70123450{i}"),
                "codigo":f"PROD-0{i}",
                "activo":[
                    {"valor":e_docs[i]["activo"],"fechaRegistro":fixed_beginning}
                    ],
                "costo":[
                    {"valor":random.uniform(35,47),"fechaRegistro":fixed_beginning}
                    ],
                "almacenes":[ 
                    {"valor":e_docs[i]["almacenes"] ,"fechaRegistro":fixed_beginning } 
                    ],
                "fechaRegistro":fixed_beginning
                } for i in range(1,6)}


update_timeline = [  ]
i = 0
for update in updates:
    update_date = update_dates[i]
    for existenciaId,doc in update.items():
        for field,value in doc:
            h_dict[existenciaId][field].append({"valor":value,"fechaRegistro":update_date})
            h_dict[existenciaId]["fechaUpdate"] = update_date
    update_timeline.append(h_dict)

h_docs =[ doc for _,doc in h_dict]
historic_table.insert_many(h_docs)




# -----------------------------------------------
# PRUEBAS
# -----------------------------------------------

def test_get_documents():

    def normalize(doc):
        doc = dict(doc)
        doc.pop("_id", None)
        return doc
    
    existence_docs,historic_docs = get_documents()

    # Comparación de información existencia
    for got, expected in zip(existence_docs, e_docs):
        assert normalize(got) == normalize(expected) ,"Los documentos recuperados deben contener el mismo contenido que los documentos referencia"

    # Comparación de información histórica
    for got, expected in zip(historic_docs, h_docs):
        assert normalize(got) == normalize(expected),"Los documentos recuperados deben contener el mismo contenido que los documentos referencia"



def test_delta_docs():
    reference_docs = h_dict.values()
    updated_docs = update_timeline[0]
    updates_docs = updates[0].values()
    
    
    for reference,updated,update in zip(reference_docs,updated_docs,updates_docs):
        existenceId = reference["existenciaId"]
        got = delta_docs(reference,updated)
        expect = update
        assert got == expect , "Se espera que la differencia entre documentos sea la información de actualización"

def test_compare_doc_size():
    cant_update_doc = 
    can_update = 



def test_update_table():



def test_main():