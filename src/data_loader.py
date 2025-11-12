import os
import json
import pyodbc
import mysql.connector
import streamlit as st
import pandas as pd
from dotenv import load_dotenv
import shutil
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

load_dotenv()


## Conexión
driver=os.getenv("DWH_DRIVER")
ip=os.getenv("DWH_IP")
uid=os.getenv("DWH_UID")
pwd=os.getenv("DWH_PASSWORD")

conn_str = (
    f'DRIVER={{{driver}}};'
    f'SERVER={ ip };'  # SQL server Ip
    'DATABASE=DWH;'  # Nombre de base
    f'UID={uid};'  # User id
    f'PWD={pwd}'   # Password
)

## Columnas Factura

table_name=os.getenv("SALES_TABLE_NAME")
date_col=os.getenv("SALES_DATE_COLUMN")
schema=os.getenv("DB_SCHEMA")
data_columns=os.getenv("SALES_DATA_COLUMNS")
sales_art_col=os.getenv("SALES_ARTICLE_COLUMN")
price_col=os.getenv("SALES_PRICE")

## Columnas producto

table = os.getenv("ART_TABLE_NAME")
art_col = os.getenv("ARTICLE_COLUMN")
art_desc = os.getenv("ARTICLE_DESCRIPTION")
art_cost = os.getenv("ARTICLE_COST")

## Conexión 
ip=os.getenv("CDB_IP")
user=os.getenv("CDB_UID")
password=os.getenv("CDB_PASSWORD")
database=os.getenv('CDB_DATABASE')
category_table=os.getenv('CDB_CATEGORY_TABLE')
product_table=os.getenv('CDB_PRODUCT_TABLE')



conn_mysql = mysql.connector.connect(
    host=ip,
    user=user,
    password=password,
    database=database
)



def build_query(start_date:str,end_date:str)->str:
    """
    Recibe fecha de inicio y final de periodo y regresa un query
    utilizado para la extracción de la tabla de facturas de venta.

    Args:
    start_date := Se espera una fecha con el formato YYYY-MM-DD
    end_date := Se espera una fecha con el formato YYYY-MM-DD
    """
    fi = datetime.strptime(start_date,"%Y-%m-%d").date()
    ff = datetime.strptime(end_date,"%Y-%m-%d").date()
    if fi > ff:
        print("Periodo invalido detectado, fecha inicio comienza después de fecha final")
        return None
    elif fi == ff:
        print("Periodo invalido detectado, fecha inicio igual a fecha final")
        return None
    
    query = f"""
                SELECT {data_columns}
                FROM {schema}.{table_name}
                WHERE {date_col} BETWEEN '{start_date}' AND '{end_date}'
                AND {price_col} > 0 

            """
    return query



def get_query(query:str,connection_str:str=conn_str)->pd.DataFrame:    
    try:
        
        conn = pyodbc.connect(connection_str)
        print("Conexión exitosa a la base de datos!")
        
        df = pd.read_sql(query, conn)
        conn.close()
        return df

    except pyodbc.Error as e:
        print(f"Error al intentar conectarse a la base de datos: {e}")


def get_last_processed_offset(offset_file: str) -> int:
    """
    Retrieve the last processed offset from a JSON file.
    If no file exists, return 0 (start from the beginning).
    """
    if os.path.exists(offset_file):
        with open(offset_file, 'r') as f:
            last_offset = json.load(f).get('last_offset', 0)
        return last_offset
    return 0

def save_last_processed_offset(offset_file: str, offset: int):
    """
    Save the last processed offset to a JSON file.
    """
    with open(offset_file, 'w') as f:
        json.dump({'last_offset': offset}, f)



def fetch_and_write_chunk(query:str,
                          chunk_index:int, 
                          offset:int, 
                          chunk_size:int, 
                          connection_str:str, 
                          order_column:str, 
                          temp_dir:str,**kwargs)->int:
    conn = pyodbc.connect(connection_str)

    query = query + f"""
        ORDER BY {order_column}
        OFFSET {offset} ROWS FETCH NEXT {chunk_size} ROWS ONLY
    """
    df = pd.read_sql(query, conn)
    conn.close()

    if not df.empty:
        temp_file = os.path.join(temp_dir, f'chunk_{chunk_index}.csv')
        df.to_csv(temp_file, index=False)
    return chunk_index

def extract_table_parallel(
    query:str,
    output_file: str,
    connection_str: str,
    chunk_percent: float = 10,
    table_name: str = table_name,
    schema: str = schema,
    order_column: str = date_col,
    offset_file: str = 'last_offset.json',
    max_workers: int = 4,
    temp_dir:str='./temp_chunks'
):
    try:
        print("Conectando para obtener número de filas...")
        n_rows = int(get_query(
            f"SELECT COUNT(*) AS NROWS FROM {schema}.{table_name}", connection_str
        )['NROWS'][0])

        offset = get_last_processed_offset(offset_file)
        chunk_size = int((chunk_percent / 100) * n_rows)
        chunk_size = max(chunk_size, 1)  # prevenir 0 chunks

        total_chunks = (n_rows - offset + chunk_size - 1) // chunk_size
        print(f"Total de filas: {n_rows}, Offset actual: {offset}")
        print(f"Procesando {total_chunks} chunks de tamaño {chunk_size}")

        
        os.makedirs(temp_dir, exist_ok=True)

        remaining_chunks = []

        for i in range(total_chunks):
            chunk_offset = i * chunk_size + offset
            chunk_file = os.path.join(temp_dir, f'chunk_{i}.csv')
            if not os.path.exists(chunk_file):
                remaining_chunks.append((i, chunk_offset))
            else:
                print(f" Chunk {i} ya existe. Saltando...")

        print(f"Chunks a procesar: {len(remaining_chunks)}")

        all_success = True

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    fetch_and_write_chunk,
                    query=query,
                    chunk_index=i,
                    offset=chunk_offset,
                    chunk_size=chunk_size,
                    connection_str=connection_str,
                    schema=schema,
                    table_name=table_name,
                    order_column=order_column,
                    temp_dir=temp_dir
                ): i for i, chunk_offset in remaining_chunks
            }

            for future in as_completed(futures):
                chunk_id = futures[future]
                try:
                    result = future.result()
                    print(f" Chunk {result} completado.")
                except Exception as e:
                    print(f" Error en chunk {chunk_id}: {e}")
                    all_success = False

        if not all_success:
            print(" Proceso incompleto. Reintenta más tarde para continuar desde donde se detuvo.")
            return

        print(" Unificando archivos...")

        with open(output_file, 'w', newline='', encoding='utf-8') as out_file:
            first = True
            for i in range(total_chunks):
                chunk_file = os.path.join(temp_dir, f'chunk_{i}.csv')
                if os.path.isfile(chunk_file):
                    with open(chunk_file, 'r', encoding='utf-8') as f:
                        if first:
                            shutil.copyfileobj(f, out_file)
                            first = False
                        else:
                            next(f)  # saltar header
                            shutil.copyfileobj(f, out_file)

       
        

        shutil.rmtree(temp_dir)
        print(f" Archivos temporales eliminados: {temp_dir}")

        shutil.rmtree(offset_file)
        print(f" Archivos temporales eliminados: {offset_file}")
        
    except Exception as e:
        print(f" Error crítico: {e}")


@st.cache_data
def load_data(start_date:str="2025-01-01",end_date:str="2025-12-31",output_file:str="data/facturas.csv")->tuple[pd.DataFrame,pd.DataFrame,pd.DataFrame]:
    """
    Función que recibe fecha de inicio y final de periodo junto con ruta de salida
    especifícada. Extrae los datos necesarios, los guarda en un archivo csv y los 
    carga en un dataframe de pandas.
    
    """
    desc_data_file_exists = os.path.exists("data/codigos_productos.csv")
    if desc_data_file_exists:
        products= pd.read_csv('data/codigos_productos.csv')
        products= products.drop(columns='Unnamed: 0')
    else:
        query = f""" 
                    SELECT {art_col},{art_desc},{art_cost}
                    FROM {table}
        """

        products = get_query(query)
        products = products.rename(columns={art_col:'PRODUCTO',art_desc:'DESCRIPCION'})
        products.to_csv('data/codigos_productos.csv')


    # Categorías y productos
    categories_exist = os.path.exists("data/categorias.parquet")
    products_exist = os.path.exists("data/productos.parquet")
    if (categories_exist & products_exist):
        categories = pd.read_parquet("data/categorias.parquet")
        products = pd.read_parquet("data/productos.parquet")
        
    else:
        cursor = conn_mysql.cursor(dictionary=True)  # devuelve resultados como diccionarios

        cursor.execute(f"SELECT * FROM {category_table};")
        rows_category = cursor.fetchall()

        cursor.execute(f"SELECT * FROM {product_table};")
        rows_products = cursor.fetchall()
        cursor.close()
        conn_mysql.close()

        categories = pd.DataFrame(rows_category)
        products = pd.DataFrame(rows_products)

        categories.to_parquet("data/categorias.parquet")
        products.to_parquet("data/productos.parquet")
    
    
    # Facturas
    query = build_query(start_date,end_date)
    extract_table_parallel(query= query ,output_file=output_file ,connection_str= conn_str)
    
    df = pd.read_csv(output_file)

    return df,categories,products



    

   