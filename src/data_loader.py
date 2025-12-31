import os
import json
import pyodbc
import mysql.connector
import streamlit as st
import pandas as pd
import pyarrow.parquet as pq
import pyarrow as pa
from dotenv import load_dotenv
import shutil
import datetime
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

today = datetime.date.today()
start_date = datetime.date(today.year, today.month, 1)
end_date = today

def format_columns(df:pd.DataFrame):

    # Obtener diccionarios de entorno
    name_dict = json.loads(os.getenv("NAME_DICT"))
    type_dict = json.loads(os.getenv("TYPE_DICT"))

    df = df.rename(columns=name_dict)

    # Asegurarse que los tipos coinciden
    cast_dict = {}
    for col, dtype in type_dict.items():
        if col in df.columns:
            if dtype == "string":
                cast_dict[col] = "large_string[pyarrow]"
                continue  
            elif dtype.startswith("float"):
                cast_dict[col] = "halffloat[pyarrow]"
            else:
                cast_dict[col] = dtype


    if cast_dict:
        df = df.astype(cast_dict)

    return df

def build_query(start_date:datetime.datetime,end_date:datetime.datetime)->str:
    """
    Recibe fecha de inicio y final de periodo y regresa un query
    utilizado para la extracción de la tabla de facturas de venta.

    Args:
    start_date := Se espera una fecha con el formato YYYY-MM-DD
    end_date := Se espera una fecha con el formato YYYY-MM-DD
    """
    
    if start_date > end_date:
        print("Periodo invalido detectado, fecha inicio comienza después de fecha final")
        return None
    elif start_date == end_date:
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



def fetch_and_write_chunk(query:str,chunk_index:int, offset:int, chunk_size:int, connection_str:str, order_column:str, 
temp_dir:str,file_format:str="parquet",**kwargs)->int:
    
    conn = pyodbc.connect(connection_str)

    query = query + f"""
        ORDER BY {order_column}
        OFFSET {offset} ROWS FETCH NEXT {chunk_size} ROWS ONLY
    """
    df = pd.read_sql(query, conn)
    conn.close()

    if not df.empty:
        if file_format=="csv":
            temp_file = os.path.join(temp_dir, f'chunk_{chunk_index}.{file_format}')
            df.to_csv(temp_file, index=False)
        if file_format=="parquet":
            temp_file = os.path.join(temp_dir, f'chunk_{chunk_index}.{file_format}')
            df.to_parquet(temp_file, index=False,engine="pyarrow")
    return chunk_index

def extract_table_parallel(query:str,output_file: str,connection_str: str,file_format:str="parquet",chunk_percent: float = 10,table_name: str = table_name,schema: str = schema,order_column: str = date_col,offset_file: str = 'last_offset.json',
max_workers: int = 4,temp_dir:str='./temp_chunks'
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
        if file_format=="csv":
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
        if file_format=="parquet":
            writer = None

            for i in range(total_chunks):
                fchunk = os.path.join(temp_dir, f"chunk_{i}.parquet")
                if os.path.isfile(fchunk):
                    table = pq.read_table(fchunk)

                    if writer is None:
                        writer = pq.ParquetWriter(output_file, table.schema)

                    writer.write_table(table)

            if writer:
                writer.close()

       
        

        shutil.rmtree(temp_dir)
        print(f" Archivos temporales eliminados: {temp_dir}")

        shutil.rmtree(offset_file)
        print(f" Archivos temporales eliminados: {offset_file}")
        
    except Exception as e:
        print(f" Error crítico: {e}")





def update_table(table:str,latest_update:str,save_dir:str="data"):
    """ 
    Se especifica cual de las tablas de datos ocupa actualizarse y el último periodo
    que tiene registrado para no generar una consulta grande.

    """
    query = build_query (start_date=latest_update,end_date=today)

    extract_table_parallel(query=query,
                           output_file=f"{save_dir}/{table}_update.parquet",
                           connection_str=conn_str,
                           file_format="parquet")
    
    update_df = pd.read_parquet(f"{save_dir}/{table}_update.parquet",dtype_backend="pyarrow")
    update_df = format_columns(update_df) 

    outdated_df = pd.read_parquet(f"{save_dir}/{table}.parquet",dtype_backend="pyarrow")
    outdated_df = format_columns(outdated_df)

    df = pd.concat([outdated_df, update_df], ignore_index=True)
    df = df.drop_duplicates(subset=["productId","folio","fecha"])
    df.to_parquet(f"{save_dir}/{table}.parquet",engine="pyarrow",index=False)


def load_product_codes():
    desc_data_file_exists = os.path.exists("data/codigos_productos.csv")
    if desc_data_file_exists:
        df = pd.read_csv('data/codigos_productos.csv')
        df = df.drop(columns='Unnamed: 0')
    else:
        query = f""" 
                    SELECT {art_col},{art_desc},{art_cost}
                    FROM {table}
        """

        df = get_query(query)
        df = df.rename(columns={art_col:'PRODUCTO',art_desc:'DESCRIPCION'})
        df.to_csv('data/codigos_productos.csv')

    return df

def load_categories():
    categories_exist = os.path.exists("data/categorias.parquet")
    if categories_exist:
        df = pd.read_parquet("data/categorias.parquet")
        
    else:
        cursor = conn_mysql.cursor(dictionary=True)  # devuelve resultados como diccionarios

        cursor.execute(f"SELECT * FROM {category_table};")
        rows_category = cursor.fetchall()

        cursor.close()
        conn_mysql.close()

        df = pd.DataFrame(rows_category)
        df.to_parquet("data/categorias.parquet")
    return df

def load_products():
    products_exist = os.path.exists("data/productos.parquet")
    if products_exist:
        
        df = pd.read_parquet("data/productos.parquet")
        
    else:
        cursor = conn_mysql.cursor(dictionary=True)  # devuelve resultados como diccionarios
        cursor.execute(f"SELECT * FROM {product_table};")
        rows_products = cursor.fetchall()
        
        cursor.close()
        conn_mysql.close()

        df = pd.DataFrame(rows_products)
        df.to_parquet("data/productos.parquet") 
    return df 

def load_invoices(source_file:str,file_format:str,start_date:str=start_date,end_date:str=end_date)->pd.DataFrame:
    """
    Recibe nombre de salida del archivo, su formato y el periodo de las facturas que se quieren
    extraer. Revisa si esta actualizada la base con ese periodo para no hacer la consulta completa. 
    """
    if file_format=="csv":
        current_df = pd.read_csv("data/facturas.csv")
        current_df = format_columns(current_df)
    if file_format=="parquet":
        current_df = pd.read_parquet("data/facturas.parquet")
        current_df = format_columns(current_df)
    if current_df.empty:
        query = build_query(start_date,end_date)
        extract_table_parallel(query= query ,output_file= source_file ,connection_str= conn_str)
    

    latest_period = current_df["fecha"].max().date()
    not_updated = latest_period < end_date
    if not_updated:
        update_table(table="facturas",latest_update=latest_period)


    if file_format=="csv":
        df = pd.read_csv(source_file)
    if file_format=="parquet":
        df = pd.read_parquet(source_file)
    
    return df


def load_data(output_file:str,file_format:str,start_date:str=start_date,end_date:str=end_date)->tuple[pd.DataFrame,pd.DataFrame,pd.DataFrame]:
    """
    Función que recibe fecha de inicio y final de periodo junto con ruta de salida
    especifícada. Extrae los datos necesarios, los guarda en un archivo csv y los 
    carga en un dataframe de pandas.
    
    """
    # Códigos de productos
    product_codes = load_product_codes()

    # Categorías y productos
    categories = load_categories()
    products= load_products()
    
    # Facturas
    invoices = load_invoices(source_file=output_file,file_format=file_format,start_date=start_date,end_date=end_date)

    return invoices,categories,products,product_codes



    

   