import os
import re
import json
import warnings 
import pyodbc
import mysql.connector
import pandas as pd
import pyarrow.parquet as pq
import shutil
import datetime
import requests
import time

from pathlib import Path
from dotenv import load_dotenv
from pymongo import MongoClient 
from pymongo.database import Database
from pymongo.errors import PyMongoError
from concurrent.futures import ThreadPoolExecutor, as_completed

load_dotenv()
warnings.filterwarnings('ignore')

# ===========================================================
#                           CONFIG
# ===========================================================

Date = datetime.date
Document =  dict[str, any]
Documents = list[Document]

DATA_PATH= Path('data')
TODAY= Date.today()
BATCH_SIZE = 500 # número de documentos colectados por batch
EXCHANGE_API_KEY = os.getenv("EXCHANGE_API_KEY")

# Tabla de existencias historicas
HISTORIC_CONN = os.getenv("HIST_MONGO_URI")
HIST_NAME= os.getenv("HIST_MONGO_DB")

# Tabla de existencias
API_CONN = os.getenv("API_MONGO_URI")
API_NAME = os.getenv("API_MONGO_DB")

## Columnas Factura
INVOICES_TABLE=os.getenv("INVOICES_TABLE_NAME")
INVOICES_TABLE_SCHEMA ='dbo' 
INVOICES_COLUMNS=os.getenv("INVOICES_DATA_COLUMNS")

## Columnas producto
PRODUCT_TABLE_NAME = os.getenv("PRODUCT_TABLE_NAME")
PRODUCT_COLUMNS= os.getenv("PRODUCT_COLUMNS")

# ===========================================================
#                           CONEXIÓN
# ===========================================================

DATA_WAREHOUSE_DRIVER=os.getenv("DATA_WAREHOUSE_DRIVER")
DATA_WAREHOUSE_DB_NAME=os.getenv("DATA_WAREHOUSE_DB_NAME")
DATA_WAREHOUSE_IP=os.getenv("DATA_WAREHOUSE_IP")
DATA_WAREHOUSE_USER_ID=os.getenv("DATA_WAREHOUSE_USER_ID")
DATA_WAREHOUSE_USER_PWD=os.getenv("DATA_WAREHOUSE_USER_PWD")

conn_str = (
    f'DRIVER={{{DATA_WAREHOUSE_DRIVER}}};'
    f'SERVER={ DATA_WAREHOUSE_IP };'  
    f'DATABASE={DATA_WAREHOUSE_DB_NAME};'  
    f'UID={DATA_WAREHOUSE_USER_ID};'  
    f'PWD={DATA_WAREHOUSE_USER_PWD}'   
)

PRODUCT_CATEGORY_TABLE_NAME=os.getenv('PRODUCT_CATEGORY_TABLE_NAME')
PRODUCT_CATALOGUE_TABLE_NAME=os.getenv('PRODUCT_CATALOGUE_TABLE_NAME')


def connect_to_DB(conn_uri:str,
                  db_name:str)-> Database|None:
    """
    Docstring 
    
    :return: Base de datos de mongoDB
    :rtype: Any
    """
    try:
        client = MongoClient(conn_uri,
                             compressors="zstd,snappy,zlib",
                             maxPoolSize=5)
        return client[db_name]
    except PyMongoError as e:
        print(f"No se pudo realizar conexión con base de datos:{e}")
        return None
    

    

def get_mysql_connection():
    return mysql.connector.connect(
    host=os.getenv("CDB_IP"),
    user=os.getenv("CDB_UID"),
    password=os.getenv("CDB_PASSWORD"),
    database=os.getenv('CDB_NAME')
)

# ===========================================================
#                           QUERIES
# ===========================================================

def build_query(start_date:Date,
                end_date:Date)->str:
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
    
    invoice_date_col = INVOICES_COLUMNS.split(',')[3]
    invoice_price_col = INVOICES_COLUMNS.split(',')[4]
    query = f"""
                SELECT {INVOICES_COLUMNS}
                FROM {INVOICES_TABLE_SCHEMA}.{INVOICES_TABLE}
                WHERE {invoice_date_col} BETWEEN '{start_date}' AND '{end_date}'
                AND {invoice_price_col} > 0 

            """
    return query

def get_query(query:str,
              connection_str:str=conn_str)->pd.DataFrame:    
    try:
        
        conn = pyodbc.connect(connection_str)
        print("Conexión exitosa a la base de datos!")
        
        df = pd.read_sql(query, conn)
        conn.close()
        return df

    except pyodbc.Error as e:
        print(f"Error al intentar conectarse a la base de datos: {e}")


def get_documents(database:None,
                  collection:str,
                  filters:dict=None,
                  projection:dict=None) -> Documents:
    """
    Función que regresa lista de documentos extraídos de la colección de existencia
    
    :return: Conjunto de documentos extraídos de la colección de existencia e historial
    :rtype: tuple
    """
    if database is not None:
        db = database
    else:
        db = connect_to_DB(API_CONN,API_NAME)

    if db is None:
        return []
    else:
        collection = db[collection]
        try:
            cursor = collection.find(filters, 
                                     projection=projection,
                                     batch_size=BATCH_SIZE)
            
            result_docs= list(cursor) 
            return result_docs
        except PyMongoError as e:
            print(f"No se pudieron extraer los documentos correctamente:{e}")
            return []
        
def get_product_cost_dict(query_fn=get_query)-> dict :
    """
    Función que consulta el datawarehouse para conseguir los costos de productos y los regresa
    como diccionario.
    
    :return: Regresa un diccionario donde las llaves son el código del producto (productId) y los valores el costo correspondiente
    :rtype: dict
    """
    product_code_col= PRODUCT_COLUMNS.split(',')[2]
    product_cost_col= PRODUCT_COLUMNS.split(',')[2]
    query = f""" SELECT {product_code_col},{product_cost_col} 
                 FROM {PRODUCT_TABLE_NAME}
            """
    df = query_fn(query)
    if df is None or df.empty:
        raise RuntimeError(
            "No se pudo obtener costos de productos. "
            "Revisa la conexión ODBC y variables de entorno."
        )    
    
    return dict(zip(df[product_code_col], df[product_cost_col]))



# ===========================================================
# TRANSFORMACIONES
# ===========================================================


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


# ===========================================================
#                       EXTRACCIÓN
# ===========================================================


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

def save_last_processed_offset(offset_file: str,
                               offset: int):
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
                          temp_dir:Path,**kwargs)->int:
    
    conn = pyodbc.connect(connection_str)

    query = query + f"""
        ORDER BY {order_column}
        OFFSET {offset} ROWS FETCH NEXT {chunk_size} ROWS ONLY
    """
    df = pd.read_sql(query, conn)
    conn.close()

    if not df.empty:
        temp_file = temp_dir/ f'chunk_{chunk_index}.parquet'
        save_file_safe(data=df,file_path=temp_file)
        
    return chunk_index

def extract_table_parallel(query:str,
                           output_file: Path,
                           connection_str: str,
                           chunk_percent: float = 10,
                           table_name: str = INVOICES_TABLE,
                           schema: str = INVOICES_TABLE_SCHEMA,
                           order_column: str = INVOICES_COLUMNS.split(',')[3],
                           offset_file: str = 'last_offset.json',
                           max_workers: int = 4,
                           temp_dir:Path=Path('/tmp')):
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
            chunk_file = temp_dir/f'chunk_{i}.parquet' 
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
            table_path = temp_dir/fname
            table = pq.read_table(table_path)
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


def get_usd_to_mxn(logger)->float:
    
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

# ===========================================================
#                      ACTUALIZACIÓN
# ===========================================================

def save_file_safe(data: pd.DataFrame, file_path: Path) -> None:
    
    file_path.parent.mkdir(parents=True, exist_ok=True)

    tmp_path = file_path.with_suffix(file_path.suffix + ".tmp")
    data.to_parquet(tmp_path, engine='pyarrow',index=False)

    os.replace(tmp_path, file_path)

def update_table(table:str,
                 latest_update:Date,
                 save_dir:Path=DATA_PATH):
    """ 
    Se especifica cual de las tablas de datos ocupa actualizarse y el último periodo
    que tiene registrado para no generar una consulta grande.

    ------------------------
    Args:

    table(str):
    latest_update(str):
    save_dir(str,optional):

    """
    if latest_update==TODAY:
        return None
    query = build_query (start_date=latest_update,end_date=TODAY)

    extract_table_parallel(query=query,
                           output_file=save_dir/f"{table}_update.parquet",
                           connection_str=conn_str)
    
    update_df = pd.read_parquet(save_dir/f"{table}_update.parquet",dtype_backend="pyarrow")
    update_df = format_columns(update_df) 

    outdated_df = pd.read_parquet(save_dir/f"{table}.parquet",dtype_backend="pyarrow")
    outdated_df = format_columns(outdated_df)

    df = pd.concat([outdated_df, update_df], ignore_index=True)
    df = df.drop_duplicates(subset=["productId","folio","date"])
    
    file_path=save_dir/f"{table}.parquet"
    save_file_safe(data=df,file_path=file_path)

    os.remove(save_dir/f"{table}_update.parquet")

def update_exchange_rates(logger,
                          rates_dataframe:pd.DataFrame,
                          rate:float=None)->pd.DataFrame:
    if rate is None:
        rate = get_usd_to_mxn(logger=logger)
    new_rate =pd.DataFrame(
            {"exchange_rate": [rate]   },
            index=pd.DatetimeIndex( [TODAY], name="date")  )
    
    new_rate.index = new_rate.index.astype("datetime64[ns]")
        
    updated_rates = (
            pd.concat([rates_dataframe, new_rate])
              .sort_index()
              .loc[~pd.concat([rates_dataframe, new_rate]).index.duplicated(keep="last")]
        )
    return updated_rates

# ===========================================================
#                       CARGA
# ===========================================================

def load_product_codes():
    file_path = DATA_PATH / 'raw' / 'codigos_productos.parquet'
    desc_data_file_exists = os.path.exists(file_path)
    if desc_data_file_exists:
        df = pd.read_parquet(file_path)
    else:
        query = f""" 
                    SELECT {PRODUCT_COLUMNS}
                    FROM {PRODUCT_TABLE_NAME}
        """
        product_code_col=PRODUCT_COLUMNS.split(',')[0]
        product_desc_col=PRODUCT_COLUMNS.split(',')[1]
        product_cost_col=PRODUCT_COLUMNS.split(',')[2]
        product_cost_coin_col=PRODUCT_COLUMNS.split(',')[3]
        product_price_coin_col=PRODUCT_COLUMNS.split(',')[4]

        df = get_query(query)
        df = df.rename(columns={product_code_col:'productId',
                                product_desc_col:'description',
                                product_cost_col:'cost',
                                product_cost_coin_col:'buy_coin',
                                product_price_coin_col:'sell_coin'})
        
        df["buy_coin" ] = df["buy_coin"].astype("int8[pyarrow]")
        df["sell_coin"] = df["sell_coin"].astype("int8[pyarrow]")

        df = df.astype({'productId':'string'}) 

        save_file_safe(data=df,file_path=file_path)
        

    return df

def load_categories():
    file_path = DATA_PATH/'raw'/'categorias.parquet'
    
    categories_exist = os.path.exists(file_path)
    if categories_exist:
        df = pd.read_parquet(file_path)
        
    else:
        conn_mysql = get_mysql_connection()
        cursor = conn_mysql.cursor(dictionary=True)  # devuelve resultados como diccionarios

        cursor.execute(f"SELECT * FROM {PRODUCT_CATEGORY_TABLE_NAME};")
        rows_category = cursor.fetchall()

        cursor.close()
        conn_mysql.close()

        df = pd.DataFrame(rows_category)
        save_file_safe(data=df,file_path=file_path)
        
    return df

def load_products():
    file_path = DATA_PATH/'raw'/'productos.parquet'
    products_exist = os.path.exists(file_path)
    if products_exist:
        
        df = pd.read_parquet(file_path)
        
    else:
        conn_mysql=get_mysql_connection()
        cursor = conn_mysql.cursor(dictionary=True)  # devuelve resultados como diccionarios
        cursor.execute(f"SELECT * FROM {PRODUCT_CATALOGUE_TABLE_NAME};")
        rows_products = cursor.fetchall()
        
        cursor.close()
        conn_mysql.close()

        df = pd.DataFrame(rows_products)
        save_file_safe(data=df,file_path=file_path)
    return df 

def load_invoices(start_date:Date= Date(TODAY.year,TODAY.month,1),
                  end_date:Date= TODAY)->pd.DataFrame:
    """
    Revisa si esta actualizada la base de facturas con el periodo específicado para no hacer la consulta completa. 
    """
    
    source_file_path = DATA_PATH/'raw'/'facturas.parquet'
    if os.path.exists(source_file_path):
        current_df = pd.read_parquet(source_file_path)
        current_df = format_columns(current_df)
    else:
        current_df = pd.DataFrame()

    if current_df.empty:
        query = build_query(start_date,end_date)
        extract_table_parallel(query= query ,
                               output_file= source_file_path ,
                               connection_str= conn_str)
        
        current_df = pd.read_parquet(source_file_path)
        current_df = format_columns(current_df)
        save_file_safe(data=current_df,file_path=source_file_path)

    latest_period = current_df['date'].max().date()
    not_updated = latest_period < end_date
    if not_updated:
        update_table(save_dir=DATA_PATH/'raw',
                     table='facturas',
                     latest_update=latest_period)


    
    df = pd.read_parquet(source_file_path)
    
    return df


def load_inventory()->pd.DataFrame:

    conn_uri = os.getenv("HIST_MONGO_URI")
    db_name = os.getenv("HIST_MONGO_DB")

    database = connect_to_DB(conn_uri,db_name)
    if database is not None:
        hist_collection = os.getenv("EXISTENCE_HIST_COLLECTION")
        docs = get_documents(database,hist_collection)

        df = pd.DataFrame(data=docs)
        df["productId"]= df["productoReferencia"].apply( lambda x:x['codigo'])

        df =( df.drop(columns=["activo",'_id','productoReferencia'])
                .rename(columns={"fechaRegistro":"date",
                                 "costo":"cost",
                                 "almacenes":"existence"}))
        
        df["date"] = df['date'].dt.strftime('%Y-%m-%d')
        df["date"] = pd.to_datetime(df["date"])

        return df
    else:
        return pd.DataFrame()


def load_branches()->pd.DataFrame:
    conn_uri = os.getenv("API_MONGO_URI")
    db_name = os.getenv("API_MONGO_DB")

    database = connect_to_DB(conn_uri,db_name)
    backup_file_path= DATA_PATH/'backup'/'branches.parquet'
    if database is None:
        if os.path.exists(backup_file_path):
            return pd.read_parquet(backup_file_path)
        else:
            return pd.DataFrame()
        
    else:
        collection = os.getenv("BRANCHES_COLLECTION")
        docs = get_documents(database,collection)

        branches = pd.DataFrame(docs)
        
        branches.drop(columns=['correos','_id','logs','__v','connect'],inplace=True)
        branches = branches.astype(dtype={'nemonico':'str',
                                          'sucursal':'str',
                                          'homoclave':'str'})
        
        save_file_safe(data=branches,file_path=backup_file_path)
        
        
        return branches
        

def load_storage()->dict:
    branches = load_branches()

    if not branches.empty :
        branches = branches[["nemonico","sucursal"]]
        branches = branches.set_index("nemonico")["sucursal"].to_dict()

        branch_storage={}
        for key,branch in branches.items():
            if branch in branch_storage.keys():
                branch_storage[branch].append(key)
                continue

            branch_storage[branch]=[key]

        return branch_storage
    else:
        return {}
    
def load_raw_exchange_rates()->pd.DataFrame:
    dir_path=DATA_PATH/'raw'
    if os.path.exists(dir_path):
        for path in os.listdir(dir_path):
            match_group = re.match(pattern='^historical_data_usd_mxn_',
                                   string=path)
            if match_group:
                file_path = dir_path/path
                break
    else:
        return None
    df = pd.read_csv(file_path,sep=";")
    df = df[["Date","Close"]]

    df = (df.rename(columns={"Date":"date",
                            "Close":"exchange_rate"})

            .astype({"date":"datetime64[ns]",
                    "exchange_rate":"float"})

            .set_index("date"))
    
    return df

def load_exchange_rates():
    file_path=DATA_PATH/'processed'/'conversion_usd_mxn.parquet'
    processed = os.path.exists(file_path)
    if processed:
        df = pd.read_parquet(file_path)
        return df
    else: 
        return None


def load_sales_invoices():
    file_path=DATA_PATH/'processed'/'facturas_ventas.parquet'
    processed = os.path.exists(file_path)
    if processed:
        df = pd.read_parquet(file_path)
        return df
    else: 
        return None

   