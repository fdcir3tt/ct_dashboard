import os
import datetime 
from common.paths import ENV_DIR
from dotenv import load_dotenv
from pymongo import MongoClient

env_path = ENV_DIR /".env"
load_dotenv(env_path)
hist_mongo_uri = os.getenv("TRACE_MONGO_URI")
hist_db_name = os.getenv("TRACE_EXISTENCE_DB_NAME")
trace_existence_collection = os.getenv("TRACE_EXISTENCE_COLLECTION")

client = MongoClient(hist_mongo_uri)
db = client[hist_db_name]
col = db[trace_existence_collection]

docs_a_borrar = col.find(
    {"productoReferencia.existenciaId": {"$type": "string"},
     "fechaRegistro": {"$gte": datetime.datetime(2026, 5, 26)}},
    {"productoReferencia": 1}  # solo traer ese campo
)

referencias = list({
    str(d["productoReferencia"]): d["productoReferencia"]
    for d in docs_a_borrar
}.values())

print(f"Referencias a borrar: {len(referencias)}")

# 2. Borra una por una con el objeto completo
for ref in referencias:
    result = col.delete_many({"productoReferencia": ref})
    print(f"Borrados: {result.deleted_count} — {ref}")