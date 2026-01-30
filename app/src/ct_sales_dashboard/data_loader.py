import os
import re
import json
import pyodbc
import mysql.connector
import streamlit as st
import pandas as pd
import pyarrow.parquet as pq
import shutil
import datetime
import requests
import time

from dotenv import load_dotenv
from pymongo import MongoClient 
from concurrent.futures import ThreadPoolExecutor, as_completed

load_dotenv()

# -----------------------------------------------------------
# SETUP 
# -----------------------------------------------------------

BATCH_SIZE = 500
HISTORIC_CONN = os.getenv("HIST_MONGO_URI")
HIST_NAME= os.getenv("HIST_MONGO_DB")
API_CONN = os.getenv("API_MONGO_URI")
API_NAME = os.getenv("API_MONGO_DB")
EXCHANGE_API_KEY = os.getenv("EXCHANGE_API_KEY")

Date = datetime.datetime
Document =  dict[str, any]
Documents = list[Document]

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
art_cost_coin = os.getenv("ARTICLE_COST_COIN")
art_price_coin = os.getenv("ARTICLE_PRICE_COIN")


today = datetime.date.today()
yesterday = today - datetime.timedelta(days=1)
start_date = datetime.date(today.year, today.month, 1)
end_date = today


# -----------------------------------------------------------
# CONEXIÓN
# -----------------------------------------------------------
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


def connect_to_DB(conn_uri,db_name)-> MongoClient:
    """
    Docstring for connect_to_DB
    
    :return: Cliente de mongoDB
    :rtype: Any
    """

    client = MongoClient(conn_uri,compressors="zstd,snappy,zlib",maxPoolSize=5)
    db = client[db_name]

    return db

# -----------------------------------------------------------
# QUERIES
# -----------------------------------------------------------

def build_query(start_date:Date,end_date:Date)->str:
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


def get_documents(database:None,collection:str,filters:dict=None,projection:dict=None) -> Documents:
    """
    Función que regresa lista de documentos extraídos de la colección de existencia
    
    :return: Conjunto de documentos extraídos de la colección de existencia e historial
    :rtype: tuple
    """
    if database is not None:
        db = database
    else:
        db = connect_to_DB(API_CONN,API_NAME)


    collection = db[collection]
    cursor = collection.find(filters, projection=projection,batch_size=BATCH_SIZE)
        
    result_docs= list(cursor) 
    return result_docs


def get_product_cost_dict(query_fn=get_query)-> dict :
    """
    Función que consulta el datawarehouse para conseguir los costos de productos y los regresa
    como diccionario.
    
    :return: Regresa un diccionario donde las llaves son el código del producto (productId) y los valores el costo correspondiente
    :rtype: dict
    """
    table = os.getenv("ART_TABLE_NAME")
    art_col = os.getenv("ARTICLE_COLUMN")
    art_cost = os.getenv("ARTICLE_COST")

    query = f""" SELECT {art_col},{art_cost} 
                 FROM {table}
            """
    df = query_fn(query)
    if df is None or df.empty:
        raise RuntimeError(
            "No se pudo obtener costos de productos. "
            "Revisa la conexión ODBC y variables de entorno."
        )    
    #cost_dict = df.set_index(art_col).to_dict(orient="index")
    return dict(zip(df[art_col], df[art_cost]))



# -----------------------------------------------------------
# TRANSFORMACIONES
# -----------------------------------------------------------


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
                cast_dict[col] = "float[pyarrow]"
            else:
                cast_dict[col] = dtype


    if cast_dict:
        df = df.astype(cast_dict)

    return df


# -----------------------------------------------------------
# EXTRACCIÓN
# -----------------------------------------------------------


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
temp_dir:str,**kwargs)->int:
    
    conn = pyodbc.connect(connection_str)

    query = query + f"""
        ORDER BY {order_column}
        OFFSET {offset} ROWS FETCH NEXT {chunk_size} ROWS ONLY
    """
    df = pd.read_sql(query, conn)
    conn.close()

    if not df.empty:
        temp_file = os.path.join(temp_dir, f'chunk_{chunk_index}.parquet')
        df.to_parquet(temp_file, index=False,engine="pyarrow")
    return chunk_index

def extract_table_parallel(query:str,output_file: str,connection_str: str,chunk_percent: float = 10,table_name: str = table_name,schema: str = schema,order_column: str = date_col,offset_file: str = 'last_offset.json',
max_workers: int = 4,temp_dir:str='/tmp'
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
            chunk_file = os.path.join(temp_dir, f'chunk_{i}.parquet')
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
        writer = None

        chunk_files = sorted(
            (f for f in os.listdir(temp_dir) if f.endswith(".parquet")),
            key=lambda x: int(x.split("_")[1].split(".")[0])
            )


        for fname in chunk_files:
            table = pq.read_table(os.path.join(temp_dir, fname))
            if writer is None:
                writer = pq.ParquetWriter(output_file, table.schema)
            else:
                if table.schema != writer.schema:
                    raise ValueError(f"Schema inconsistente en {fname}")

            writer.write_table(table)


        writer.close()
        

        time.sleep(0.2)  # deja que Windows libere handles

        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=False)
        print(f" Archivos temporales eliminados: {temp_dir}")

        if os.path.exists(offset_file):
            os.remove(offset_file)
        print(f" Archivos temporales eliminados: {offset_file}")
        
    except Exception as e:
        print(f" Error crítico: {e}")


def get_usd_to_mxn(logger,date:datetime.datetime = datetime.datetime.today())->float:
    
    url = "https://api.fxratesapi.com/latest"
    params = {
            "api_key": EXCHANGE_API_KEY,
            "base": "USD",
            "currencies": "MXN",
            "resolution": "1d",
            "amount": 1,
            "places": 6,
            "format": "json"
            }
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException:
        logger.exception("FX rates API request failed")
        return None

    try:
        data = response.json()
    except json.JSONDecodeError:
        logger.exception(
            "Failed to decode JSON from FX rates API",
            extra={"response_text": response.text},
        )
        return None

    try:
        return data["rates"]["MXN"]
    except KeyError:
        logger.error(
            "MXN rate missing from API response",
            extra={"response_json": data},
        )
        return None

# -----------------------------------------------------------
# ACTUALIZACIÓN
# -----------------------------------------------------------


def update_table(table:str,latest_update:str,save_dir:str="data"):
    """ 
    Se especifica cual de las tablas de datos ocupa actualizarse y el último periodo
    que tiene registrado para no generar una consulta grande.

    ------------------------
    Args:

    table(str):
    latest_update(str):
    save_dir(str,optional):

    """
    if latest_update==today:
        return None
    query = build_query (start_date=latest_update,end_date=today)

    extract_table_parallel(query=query,
                           output_file=f"{save_dir}/{table}_update.parquet",
                           connection_str=conn_str)
    
    update_df = pd.read_parquet(f"{save_dir}/{table}_update.parquet",dtype_backend="pyarrow")
    update_df = format_columns(update_df) 

    outdated_df = pd.read_parquet(f"{save_dir}/{table}.parquet",dtype_backend="pyarrow")
    outdated_df = format_columns(outdated_df)

    df = pd.concat([outdated_df, update_df], ignore_index=True)
    df = df.drop_duplicates(subset=["productId","folio","date"])
    df.to_parquet(f"{save_dir}/{table}.parquet",engine="pyarrow",index=False)

    os.remove(f"{save_dir}/{table}_update.parquet")

def update_exchange_rates(logger,rates_dataframe:pd.DataFrame,rate:float=None)->pd.DataFrame:
    if rate is None:
        rate = get_usd_to_mxn(logger=logger)
    new_rate =pd.DataFrame(
            {"exchange_rate": [rate]   },
            index=pd.DatetimeIndex( [datetime.datetime.today()], name="date")  )
    
    new_rate.index = new_rate.index.astype("datetime64[ns]")
        
    updated_rates = (
            pd.concat([rates_dataframe, new_rate])
              .sort_index()
              .loc[~pd.concat([rates_dataframe, new_rate]).index.duplicated(keep="last")]
        )
    return updated_rates

# -----------------------------------------------------------
# CARGA
# -----------------------------------------------------------

def load_product_codes():
    desc_data_file_exists = os.path.exists("data/raw/codigos_productos.parquet")
    if desc_data_file_exists:
        df = pd.read_parquet('data/raw/codigos_productos.parquet')
    else:
        query = f""" 
                    SELECT {art_col},{art_desc},{art_cost},{art_cost_coin},{art_price_coin}
                    FROM {table}
        """

        df = get_query(query)
        df = df.rename(columns={art_col:'productId',art_desc:'description',art_cost:'cost',art_cost_coin:'buy_coin',art_price_coin:'sell_coin'})
        df["buy_coin" ] = df["buy_coin"].astype("int8[pyarrow]")
        df["sell_coin"] = df["sell_coin"].astype("int8[pyarrow]")
        df = df.astype({'productId':'string'}) 
        df.to_parquet('data/raw/codigos_productos.parquet',index=False)

    return df

def load_categories():
    categories_exist = os.path.exists("data/raw/categorias.parquet")
    if categories_exist:
        df = pd.read_parquet("data/raw/categorias.parquet")
        
    else:
        cursor = conn_mysql.cursor(dictionary=True)  # devuelve resultados como diccionarios

        cursor.execute(f"SELECT * FROM {category_table};")
        rows_category = cursor.fetchall()

        cursor.close()
        conn_mysql.close()

        df = pd.DataFrame(rows_category)
        df.to_parquet("data/raw/categorias.parquet")
    return df

def load_products():
    products_exist = os.path.exists("data/raw/productos.parquet")
    if products_exist:
        
        df = pd.read_parquet("data/raw/productos.parquet")
        
    else:
        cursor = conn_mysql.cursor(dictionary=True)  # devuelve resultados como diccionarios
        cursor.execute(f"SELECT * FROM {product_table};")
        rows_products = cursor.fetchall()
        
        cursor.close()
        conn_mysql.close()

        df = pd.DataFrame(rows_products)
        df.to_parquet("data/raw/productos.parquet") 
    return df 

def load_invoices(start_date:str=start_date,end_date:str=end_date)->pd.DataFrame:
    """
    Revisa si esta actualizada la base de facturas con el periodo específicado para no hacer la consulta completa. 
    """
    
    source_file = "data/raw/facturas.parquet"
    if os.path.exists("data/raw/facturas.parquet"):
        current_df = pd.read_parquet("data/raw/facturas.parquet")
        current_df = format_columns(current_df)
    else:
        current_df = pd.DataFrame()

    if current_df.empty:
        query = build_query(start_date,end_date)
        extract_table_parallel(query= query ,output_file= source_file ,connection_str= conn_str)
        current_df = pd.read_parquet(source_file)
        current_df = format_columns(current_df)
        current_df.to_parquet(source_file,engine="pyarrow",index=False)

    latest_period = current_df["date"].max().date()
    not_updated = latest_period < end_date
    if not_updated:
        update_table(save_dir="data/raw",table="facturas",latest_update=latest_period)


    
    df = pd.read_parquet(source_file)
    
    return df

@st.cache_data
def load_inventory()->pd.DataFrame:

    conn_uri = os.getenv("HIST_MONGO_URI")
    db_name = os.getenv("HIST_MONGO_DB")

    database = connect_to_DB(conn_uri,db_name)

    hist_collection = os.getenv("EXISTENCE_HIST_COLLECTION")
    docs = get_documents(database,hist_collection)

    df = pd.DataFrame(data=docs)
    df["productId"]= df["productoReferencia"].apply( lambda x:x['codigo'])

    df = df.drop(columns=["activo",'_id','productoReferencia']).rename(columns={"fechaRegistro":"date","costo":"cost","almacenes":"existence"})
    df["date"] = df['date'].dt.strftime('%Y-%m-%d')
    df["date"] = pd.to_datetime(df["date"])

    return df

@st.cache_data
def load_branches()->pd.DataFrame:
    conn_uri = os.getenv("API_MONGO_URI")
    db_name = os.getenv("API_MONGO_DB")

    database = connect_to_DB(conn_uri,db_name)

    collection = os.getenv("BRANCHES_COLLECTION")
    docs = get_documents(database,collection)

    branches = pd.DataFrame(docs)
    return branches
    


@st.cache_data
def load_storage()->dict:
    branches = load_branches()
    branches = branches[["nemonico","sucursal"]]
    branches = branches.set_index("nemonico")["sucursal"].to_dict()

    branch_storage={}
    for key,branch in branches.items():
        if branch in branch_storage.keys():
            branch_storage[branch].append(key)
            continue

        branch_storage[branch]=[key]

    return branch_storage

def load_raw_exchange_rates()->pd.DataFrame:
    if os.path.exists("data/raw"):
        for path in os.listdir("data/raw"):
            match_group = re.match(pattern="^historical_data_usd_mxn_",string=path)
            if match_group:
                file_path = "data/raw"+"/"+path
                break
    else:
        return None
    df = pd.read_csv(file_path,sep=";")
    df = df[["Date","Close"]]
    df = df.rename(columns={"Date":"date","Close":"exchange_rate"})
    df = df.astype({"date":"datetime64[ns]","exchange_rate":"float"})
    df = df.set_index("date")
    return df

def load_exchange_rates():
    processed = os.path.exists("data/processed/conversion_usd_mxn.parquet")
    if processed:
        df = pd.read_parquet("data/processed/conversion_usd_mxn.parquet")
        return df
    else: 
        return None




        

   