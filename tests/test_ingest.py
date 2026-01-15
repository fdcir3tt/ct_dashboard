import pytest
import pandas as pd
import os
import mongomock
import random
import datetime as dt
from bson import ObjectId
from dotenv import load_dotenv
from  src.ingest import *


load_dotenv()


fixed_beginning = dt.datetime(2024, 1, 1, 12, 0, 0, tzinfo=dt.timezone.utc)
fixed_today = dt.datetime(2025, 12, 16, 11, 27, 0, tzinfo=dt.timezone.utc)
random.seed(42)

# -----------------------------------------------
# BASE DE DATOS FALSA
# -----------------------------------------------

# MONGO
@pytest.fixture
def mongo_db():
    """
    Base falsa de prueba
    """
    client = mongomock.MongoClient()
    return client["test_db"]


def random_date(start:dt.datetime, end:dt.datetime, seed =None)->dt.datetime:
    """
    Escoge una fecha aleatoria dentro del periodo seleccionado
    """
    rng = random.Random(seed)
    delta = end - start
    int_delta = delta.total_seconds()
    random_second = rng.randint(0, int(int_delta))
    return start + dt.timedelta(seconds=random_second)




# -----------------------------------------------
# PRUEBAS
# -----------------------------------------------

def test_get_documents_filters_and_projects(mongo_db,monkeypatch):
    """
    Prueba que verifica si la extracción de documentos de colecciones de la base de datos funciona correctamente
    """
    existence = mongo_db["existence"]
    

    existence.insert_many([
        {"codigo": "PROD1", "activo": True, "almacenes": [{"almacen":"01A","existencia": 5}]},
        {"codigo": "PROD2", "activo": True, "almacenes": [{"almacen":"03A","existencia": 1}]}
    ])
    

    monkeypatch.setenv("EXISTENCE_COLLECTION", "existence")

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

    exist_docs = get_documents(mongo_db,collection,filters,projection)

    assert len(exist_docs) == 2,"Solo existen 2 documentos dentro de la colección falsa"
    assert exist_docs[0]["codigo"] == "PROD1" , "La información de los documentos extraídos debe ser la esperada"
    assert "_id" in exist_docs[0],"Los documentos extraídos deben tener un campo identificador '_id' "

    


def test_get_product_cost_dict(monkeypatch):
    """
    Prueba que verifica que el método de extracción de costos de los productos sea correcto
    """
    df = pd.DataFrame({
        "codigo": ["PROD1", "PROD2"],
        "costo": [10.0, 20.0]
    })

    monkeypatch.setenv("ART_TABLE_NAME", "table")
    monkeypatch.setenv("ARTICLE_COLUMN", "codigo")
    monkeypatch.setenv("ARTICLE_COST", "costo")

    result = get_product_cost_dict(lambda _: df)

    assert result == {"PROD1": 10.0, "PROD2": 20.0},"Los costos extraídos deben ser los esperados"


def test_make_observation():
    """
    Prueba que verifica que la generación de observaciones 
    """
    now = dt.datetime(2024, 1, 1, 12, 0, 0)
    raw_doc = { "_id":ObjectId("64f1a2b3c4d5e6f701234501"),
             "codigo":"PROD-01",
             "activo":True,
             "fechaRegistro":fixed_beginning,
             "listaPrecios":{ 
                f"precio{k}":k*10 for k in range(1,11)
                },
             "existencia":{
                "pedido":5,
                "asignado":5
                },
             "almacenes":[ 
                { "almacen":f"{j}A","existencia":10 } for j in range(54) 
                ],
             "codigoSAT":2000,
             "updatedExistencia":random_date(fixed_beginning,fixed_today,seed=42),
             "updateExistencia":random_date(fixed_beginning,fixed_today,seed=69) }


    productId = raw_doc["codigo"]
    cost_dict = {"PROD-01":10}

    result = make_observation(raw_doc, cost_dict, now)

    # Campos correctos
    assert result["fechaRegistro"] == now,"La fecha de registro debe ser la misma que la de extracción de documentos"
    assert result["productoReferencia"]["existenciaId"] == raw_doc["_id"],"El campo debe contener el id del documento origen"
    assert result["productoReferencia"]["codigo"] == "PROD-01","El campo debe contener el código del producto"
    assert result["activo"] is True,"Campo debe coincidir con la información de origen"
    assert result["costo"] == 10,"Campo debe coincidir con la información de origen"
    assert result["almacenes"]== { f"{j}A":10 for j in range(54)},"Campo debe coincidir con la información de origen"



def test_log_collection_size(monkeypatch):
    class FakeDB:
        def command(self, *_):
            return {
                "count": 5,
                "size": 100,
                "storageSize": 120,
                "totalSize": 150
            }

    logs = []

    def fake_logger(msg):
        logs.append(msg)

    log_collection_size(FakeDB(), "test", fake_logger, num_inserted_docs=3)

    assert "inserted=3" in logs[0]
    assert "count=5" in logs[0]

def test_main_happy_path(mongo_db,monkeypatch):
    """
    Prueba que verifica si el script de ingesta funciona de forma adecuada
    """
    history = mongo_db["history"]

    monkeypatch.setenv("EXISTENCE_HIST_COLLECTION", "history")


    fake_docs = [{"_id": 1, "codigo": "PROD1", "activo": True, "almacenes": []}]
    fake_costs = {"PROD1": 10}

    calls = {"docs": 0, "costs": 0}
    called = {}

    def fake_get_docs(mongo_db,*args):
        calls["docs"] += 1
        return fake_docs

    def fake_get_costs():
        calls["costs"] += 1
        return fake_costs

    def fake_make_obs(doc, costs, now):
        called["doc"] = doc
        called["costs"] = costs
        called["now"] = now
        return {"ok": True}


    logs = []

    main(
        extract_database=mongo_db,
        insert_database=mongo_db,
        now=dt.datetime(2024, 1, 1),
        get_docs_fn=fake_get_docs,
        get_costs_fn=fake_get_costs,
        make_obs_fn=fake_make_obs,
        log_fn=lambda *args, **kwargs: logs.append("logged")
    )

    
   
    assert calls["docs"] == 1,"Método de extracción de documentos solo debe ser llamado una vez"
    assert calls["costs"] == 1,"Método de extracción de costos solo debe ser llamado una vez"

    # Contenido
    doc = history.find_one()
    assert doc["ok"] is True
    assert called["doc"] == fake_docs[0]
    assert called["costs"] == fake_costs
    assert called["now"] == dt.datetime(2024, 1, 1)



    assert logs == ["logged"],"Debe llevarse a cabo el logeo de los resultados de la inserción"


    assert history.count_documents({}) == 1,"Solo un documento debió ser insertado"
    assert list(history.find()).__len__() == len(fake_docs),"Deben haber la misma cantidad de documentos falsos de inserción que la cantidad de documentos insertados"