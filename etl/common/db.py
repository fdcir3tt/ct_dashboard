import os
import io
import uuid
import pandas as pd

from psycopg.connection import Connection,Cursor
from psycopg import sql
from typing import Any
from pymongo import MongoClient 
from pymongo.database import Database
from pymongo.errors import PyMongoError


def connect_to_mongo_db(conn_uri:str,db_name:str)-> Database|None:
    """
    Conexión a una base de mongo
    
    Parametros:
    - conn_uri: str, URI para establecer conexión
    - db_name: str, Nombre de base

    Regresa : 
    - client[db_name]: pymongo.database.Database , Base de datos de mongoDB
    """
    try:
        client = MongoClient(conn_uri,
                             compressors="zstd,snappy,zlib",
                             maxPoolSize=5)
        return client[db_name]
    except PyMongoError as e:
        print(f"No se pudo realizar conexión con base de datos:{e}")
        return None

def get_documents(database:Database|None,collection_name:str,filters:dict[str,dict]=None,projection:dict[str,str]=None,batch_size:int=500) -> list[dict[str,Any]]:
    """
    Función que regresa lista de documentos extraídos de la colección 'existencia' de productos en base de mongo
    
    Parametros:
    - database: pymongo.database.Database , Base de datos de mongo
    - collection_name: str , Nombre de colección dentro de base
    - filters: dict[str,dict] , Filtros de consulta a colección. Ver documentación de pymongo.database.Database.Collection.find() para más información
    - projection: dict[str,str] , Especificación de campos que se quieren extraer de la consulta. Ver documentación de pymongo.database.Database.Collection.find() para más información
    
    Regresa:
    - result_docs: list[dict[str,Any]], Conjunto de documentos extraídos de la colección de existencia e historial
    
    """
    if database is not None:
        db = database
    

    if db is None:
        return []
    else:
        collection = db[collection_name]
        try:
            cursor = collection.find(filter=filters, 
                                     projection=projection,
                                     batch_size=batch_size)
            
            result_docs= list(cursor) 
            return result_docs
        except PyMongoError as e:
            print(f"No se pudieron extraer los documentos correctamente:{e}")
            return []


def _copy_df(cur, df: pd.DataFrame, table_name: str):

    buffer = io.StringIO()
    df.to_csv(buffer, index=False, header=False)
    buffer.seek(0)

    cols = ", ".join(df.columns)

    copy_sql = f"COPY {table_name} ({cols}) FROM STDIN WITH CSV"

    with cur.copy(copy_sql) as copy:
        copy.write(buffer.read())

def insert_df(conn, table_name: str, df: pd.DataFrame):

    with conn.cursor() as cur:
        _copy_df(cur, df, table_name)

    conn.commit()


def create_table(hook, schema: str, table_name: str, format: dict[str, str], if_not_exists=True):

    cols = ", ".join(
        f"{col} {dtype}" for col, dtype in format.items()
    )

    query = f"""
        CREATE TABLE {"IF NOT EXISTS" if if_not_exists else ""} {schema}.{table_name} (
            {cols}
        );
    """

    hook.run(query)

def replace_table(hook, schema: str, table_name: str, format: dict[str, str], df: pd.DataFrame):

    conn = hook.get_conn()

    with conn.cursor() as cur:
        cur.execute(
            sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
                sql.Identifier(schema),
                sql.Identifier(table_name)
            )
        )

    create_table(hook, schema, table_name, format, if_not_exists=False)

    with conn.cursor() as cur:
        _copy_df(cur, df, f"{schema}.{table_name}")


def upsert_df(hook, schema: str, table_name: str, df, key_columns):

    conn = hook.get_conn()

    cols = list(df.columns)

    update_cols = [c for c in cols if c not in key_columns]

    
    if not update_cols:
        raise ValueError(
            f"No columns to update in {schema}.{table_name}. "
            f"All columns are keys: {key_columns}"
        )

    query = f"""
        INSERT INTO {schema}.{table_name} ({", ".join(cols)})
        VALUES ({", ".join(["%s"] * len(cols))})
        ON CONFLICT ({", ".join(key_columns)})
        DO UPDATE SET {", ".join(
            f"{c}=EXCLUDED.{c}" for c in update_cols
        )}
    """

    with conn.cursor() as cur:
        cur.executemany(query, df.values.tolist())

    conn.commit()