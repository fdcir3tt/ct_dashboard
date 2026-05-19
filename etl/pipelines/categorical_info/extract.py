import os
import MySQLdb 
import pyodbc

from typing import Any
from dotenv import load_dotenv
from common.registry import register
from common.paths import ENV_DIR
from common.db import connect_to_mongo_db,get_documents



env_path = ENV_DIR /".env"
load_dotenv(env_path)
mongo_uri = os.getenv("API_MONGO_URI")
public_API = os.getenv("API_MONGO_DB_NAME")

extracted_conditions = {"product_category_rows" :"skip",
                        "product_catalogue_rows":"skip",
                        "clients_data"          :"stop",
                        "product_codes_data"    :"stop",
                        "branch_docs"           :"stop" }

data_ware_house_conn_info = {"driver":os.getenv("DATA_WAREHOUSE_DRIVER"),
                             "server":os.getenv ("DATA_WAREHOUSE_IP"),
                             "database":os.getenv("DATA_WAREHOUSE_DB_NAME"),
                             "uid":os.getenv("DATA_WAREHOUSE_USER_ID"),
                             "password":os.getenv("DATA_WAREHOUSE_USER_PWD")}

product_info = {"categories" : os.getenv("PRODUCT_CATEGORY_TABLE_NAME"),
                "catalogue" : os.getenv("PRODUCT_CATALOGUE_TABLE_NAME"),
                "table_name" : os.getenv("PRODUCT_TABLE_NAME"),
                "columns" : os.getenv("PRODUCT_COLUMNS")}

category_db_conn_info = {"host":os.getenv("CDB_IP"),
                         "user":os.getenv("CDB_UID"),
                         "password":os.getenv("CDB_PASSWORD"),
                         "database":os.getenv('CDB_NAME')}

client_table_info ={ "id_column":os.getenv("ID_COLUMN"),
                     "city_column":os.getenv("CITY_COLUMN"),
                     "table_name":os.getenv("CLIENTS_TABLE_NAME")}

branches_info = {"collection":os.getenv("BRANCHES_COLLECTION")}
tag = "categorical_info"
@register(tag)
def extract_product_category_rows(**kwargs)->list[dict[str,str]]:
    try:
        with MySQLdb.connect(host=category_db_conn_info["host"],
                            user=category_db_conn_info["user"],
                            password=category_db_conn_info["password"],
                            database=category_db_conn_info["database"]) as conn:
            
            cursor = conn.cursor(MySQLdb.cursors.DictCursor)  # devuelve resultados como diccionarios
            cursor.execute(f"""SELECT idCategoria as category_id,
                                    idPadre as parent_id,
                                    nombre as category 
                            FROM {product_info["categories"]};""")
            product_category_rows = list(cursor.fetchall())
    except Exception as e:
        print(f"Error al extraer información de categorías de producto:{e}")
        product_category_rows = []
    return product_category_rows

@register(tag)
def extract_product_catalogue_rows(**kwargs)->list[dict[str,str]]:
    try :
        with MySQLdb.connect(host=category_db_conn_info["host"],
                            user=category_db_conn_info["user"],
                            password=category_db_conn_info["password"],
                            database=category_db_conn_info["database"]) as conn:
            
            cursor = conn.cursor(MySQLdb.cursors.DictCursor)  # devuelve resultados como diccionarios
        

            cursor.execute(f"""SELECT idCategoria as category_id,
                                    clave as product_id
                            FROM {product_info["catalogue"]};""")
            product_catalogue_rows = list(cursor.fetchall())
    except Exception as e:
        print(f"Error al extraer información de productos:{e}")
        product_catalogue_rows = []

    return product_catalogue_rows

@register(tag)
def extract_clients_data(**kwargs)->list[dict[str,Any]]:
    connection_str = (
            f'DRIVER={{{data_ware_house_conn_info["driver"]}}};'
            f'SERVER={  data_ware_house_conn_info["server"]  };'  
            f'DATABASE={data_ware_house_conn_info["database"]};'  
            f'UID={     data_ware_house_conn_info["uid"]     };'  
            f'PWD={     data_ware_house_conn_info["password"]}'   
        )
    with pyodbc.connect(connection_str) as conn :
        cursor = conn.cursor()
        query = f""" SELECT {client_table_info['id_column']} as client_id,
                            {client_table_info["city_column"]} as city
                     FROM   {client_table_info["table_name"]}"""
        
        cursor.execute(query)

        columns = [col[0] for col in cursor.description]
        client_list = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
    return client_list   

@register(tag)
def extract_product_codes_data(**kwargs)->list[dict[str,Any]]:
    connection_str = (
            f'DRIVER={{{data_ware_house_conn_info["driver"]}}};'
            f'SERVER={  data_ware_house_conn_info["server"]  };'  
            f'DATABASE={data_ware_house_conn_info["database"]};'  
            f'UID={     data_ware_house_conn_info["uid"]     };'  
            f'PWD={     data_ware_house_conn_info["password"]}'   
        )
    with pyodbc.connect(connection_str) as conn :
        cursor = conn.cursor()
        
        query = f""" SELECT {product_info["columns"]} FROM {product_info["table_name"]}
            """
        cursor.execute(query)
        columns = [col[0] for col in cursor.description]
        product_codes = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        for doc in product_codes:
            doc["ART_COS"] = float(doc.get("ART_COS"))
            doc["ART_MCOM"] = int(doc.get("ART_MCOM"))
            doc["ART_MVEN"] = int(doc.get("ART_MVEN"))
    return product_codes 

@register(tag)
def extract_branch_docs(**kwargs)->list[dict[str,Any]]:
    database = connect_to_mongo_db(mongo_uri,public_API)

    collection = branches_info["collection"]
    consult_info = {"filters":None,
                    "fields":{"_id":0,"nemonico":1,"sucursal":1,"homoclave":1} 
                       }    
    branch_docs = get_documents(database,collection,consult_info["filters"],consult_info["fields"])
    return branch_docs
    



