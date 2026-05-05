import os
import MySQLdb 
import pyodbc

from dotenv import load_dotenv
from common.paths import ENV_DIR
from common.db import connect_to_mongo_db,get_documents

env_path = ENV_DIR /".env"
load_dotenv(env_path)
mongo_uri = os.getenv("API_MONGO_URI")
public_API = os.getenv("API_MONGO_DB_NAME")
product_categories = os.getenv("PRODUCT_CATEGORY_TABLE_NAME")
product_catalogue = os.getenv("PRODUCT_CATALOGUE_TABLE_NAME")
product_table_name = os.getenv("PRODUCT_TABLE_NAME")
product_columns = os.getenv("PRODUCT_COLUMNS")


def extract()->tuple[list,list,list]:
    with MySQLdb.connect(host=os.getenv("CDB_IP"),user=os.getenv("CDB_UID"),password=os.getenv("CDB_PASSWORD"),database=os.getenv('CDB_NAME')) as conn:
        print("Extrayendo categorías de producto...")
    # Categorías de producto 
        cursor = conn.cursor(MySQLdb.cursors.DictCursor)  # devuelve resultados como diccionarios
        cursor.execute(f"""SELECT idCategoria as categoryId,
                                  idPadre as parentId,
                                  nombre as category 
                           FROM {product_categories};""")
        product_category_rows = list(cursor.fetchall())

        cursor.execute(f"""SELECT idCategoria as categoryId,
                                  clave as productId
                        FROM {product_catalogue};""")
        product_catalogue_rows = list(cursor.fetchall())

    
    print("Extrayendo lista de clientes...")
    # Clientes 
    connection_str = (
            f'DRIVER={{{os.getenv("DATA_WAREHOUSE_DRIVER")}}};'
            f'SERVER={os.getenv ("DATA_WAREHOUSE_IP") };'  
            f'DATABASE={os.getenv("DATA_WAREHOUSE_DB_NAME")};'  
            f'UID={os.getenv("DATA_WAREHOUSE_USER_ID")};'  
            f'PWD={os.getenv("DATA_WAREHOUSE_USER_PWD")}'   
        )
    with pyodbc.connect(connection_str) as conn :
        cursor = conn.cursor()
        query = f""" SELECT {os.getenv("ID_COLUMN")} as clientId,
                            {os.getenv("CITY_COLUMN")} as city
                     FROM {os.getenv("CLIENTS_TABLE_NAME")}"""
        
        cursor.execute(query)

        columns = [col[0] for col in cursor.description]
        client_list = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
        print("Extrayendo información de productos...")
    # Códigos de productos
        query = f""" SELECT {product_columns} FROM {product_table_name}
            """
        cursor.execute(query)
        columns = [col[0] for col in cursor.description]
        product_codes = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
    
    # Almacenes           
        database = connect_to_mongo_db(mongo_uri,public_API)

        collection = os.getenv("BRANCHES_COLLECTION")
        consult_info = {"filters":None,
                        "fields":{"_id":0,"nemonico":1,"sucursal":1,"homoclave":1} 
                       }    
        branch_docs = get_documents(database,collection,consult_info["filters"],consult_info["fields"])

        
        
        
        
        
        
    return product_catalogue_rows,product_category_rows,client_list,product_codes,branch_docs     
    
def run_extract(**context):
    extracted_data = extract()
    context["ti"].xcom_push(key="product_catalogue_rows", value=extracted_data[0])
    context["ti"].xcom_push(key="product_category_rows", value=extracted_data[1])
    context["ti"].xcom_push(key="client_list", value=extracted_data[2])
    context["ti"].xcom_push(key="product_codes", value=extracted_data[3])
    context["ti"].xcom_push(key="branch_docs", value=extracted_data[4])
