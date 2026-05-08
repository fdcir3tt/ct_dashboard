import os
import datetime 

from pymongo.database import Collection
from typing import Any
from dotenv import load_dotenv
from common.db import connect_to_mongo_db,get_documents
from common.paths import ENV_DIR
from common.data import save_data

env_path = ENV_DIR /".env"
load_dotenv(env_path)

mongo_uri = os.getenv("API_MONGO_URI")
public_API = os.getenv("API_MONGO_DB_NAME")

hist_mongo_uri = os.getenv("TRACE_MONGO_URI")
hist_db_name = os.getenv("TRACE_EXISTENCE_DB_NAME")

existence_collection = os.getenv("EXISTENCE_COLLECTION")
trace_existence_collection = os.getenv("TRACE_EXISTENCE_COLLECTION")


def check_database_up_to_date(collection:Collection, date_field: str = 'createdAt') -> bool:
    """
    Revisa si la base contiene documentos del día de hoy
    
    Args:
        collection: MongoDB collection object
        date_field: The field name that contains the date (e.g., 'createdAt', 'updatedAt')
    
    Returns:
        Dict with keys:
            - is_up_to_date (bool): True if documents exist from today
            - today_count (int): Number of documents from today
            - today_date (datetime): Today's date
    """
    try:
        
        today_start = datetime.datetime.combine(datetime.datetime.today(), datetime.time.min)
        today_end = datetime.datetime.combine(datetime.datetime.today(), datetime.time.max)
        
        # Query for documents created today
        today_count = collection.count_documents({
            date_field: {
                '$gte': today_start,
                '$lte': today_end
            }
        })
        
        return  today_count > 0
        
    except Exception as e:
        raise Exception(f"Error checking database status: {str(e)}")

def extract()->list[dict[str,Any]]|None:
    hist_database = connect_to_mongo_db(hist_mongo_uri,hist_db_name)
    if check_database_up_to_date(hist_database["tbl_existenciasHistorial"]):
        print("Collección historial de existencias ya se encuentra actualizada!")
        return None

    exist_database = connect_to_mongo_db(mongo_uri,public_API)
    consult_info = {"filters":{"almacenes.existencia": {"$gt": 0} },
                    "fields":{"codigo":1,"activo":1,"almacenes":1,"_id":1} 
                       }          
        
    documents = get_documents(exist_database,existence_collection,consult_info["filters"],consult_info["fields"])
    print(f"Cantidad de docs extraídos:{len(documents)}")
    for doc in documents:
        doc["_id"] = str(doc.get("_id"))
    return documents

def run_extract(**context):

    extracted_data = extract()
    is_up_to_date = extracted_data is None
    
    product_existences_path = "/tmp/product_existences.json"
    save_data(extracted_data,product_existences_path)
    
    context["ti"].xcom_push(key="product_existences_path", value=product_existences_path)
    context["ti"].xcom_push(key="up_to_date", value=is_up_to_date)