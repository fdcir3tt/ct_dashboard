import io
import pandas as pd

from psycopg import sql
from typing import Any
from pymongo import MongoClient 
from pymongo.database import Database
from pymongo.errors import PyMongoError


def connect_to_mongo_db(conn_uri:str,db_name:str)-> Database|None:
    """
    Conecta a una base de datos MongoDB y devuelve el objeto de base de datos.

    Parameters
    ----------
    conn_uri : str
        URI de conexión para el servidor MongoDB.
    db_name : str
        Nombre de la base de datos a la que se desea conectar.

    Returns
    -------
    Database or None
        Instancia de `pymongo.database.Database` si la conexión es exitosa,
        de lo contrario `None`.

    Notes
    -----
    Utiliza `MongoClient` con compresión habilitada (zstd, snappy, zlib)
    y un tamaño máximo de pool de 5 conexiones.
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
    Recupera documentos de una colección en MongoDB.

    Parameters
    ----------
    database : Database or None
        Base de datos de MongoDB.
    collection_name : str
        Nombre de la colección de la cual se extraen los documentos.
    filters : dict[str, dict], optional
        Filtros de consulta compatibles con `pymongo.Collection.find`.
    projection : dict[str, str], optional
        Especificación de campos a incluir o excluir en la consulta.
    batch_size : int, default=500
        Tamaño de lote para la recuperación de documentos.

    Returns
    -------
    list of dict
        Lista de documentos obtenidos de la colección.
        Devuelve una lista vacía si ocurre un error o la base es `None`.

    Notes
    -----
    Si `database` es `None`, la función retorna inmediatamente una lista vacía.
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
    """
    Copia un DataFrame hacia una tabla SQL usando el comando COPY.

    Parameters
    ----------
    cur : cursor
        Cursor de base de datos compatible con `copy`.
    df : pandas.DataFrame
        DataFrame a insertar.
    table_name : str
        Nombre de la tabla destino.

    Notes
    -----
    Utiliza un buffer en memoria (`StringIO`) para realizar la carga en formato CSV.
    No realiza commits; debe ejecutarse dentro de una transacción externa.
    """
    buffer = io.StringIO()
    df.to_csv(buffer, index=False, header=False)
    buffer.seek(0)

    cols = ", ".join(df.columns)

    copy_sql = f"COPY {table_name} ({cols}) FROM STDIN WITH CSV"

    with cur.copy(copy_sql) as copy:
        copy.write(buffer.read())

def insert_df(conn, table_name: str, df: pd.DataFrame):
    """
    Inserta un DataFrame en una tabla SQL utilizando COPY.

    Parameters
    ----------
    conn : connection
        Conexión a la base de datos.
    table_name : str
        Nombre de la tabla destino.
    df : pandas.DataFrame
        Datos a insertar.

    Notes
    -----
    Realiza commit automático después de la inserción.
    """
    with conn.cursor() as cur:
        _copy_df(cur, df, table_name)

    conn.commit()


def create_table(hook, schema: str, table_name: str, format: dict[str, str], if_not_exists=True,foreign_keys:dict[str,str]=None):
    """
    Crea una tabla en la base de datos.

    Parameters
    ----------
    hook : object
        Objeto con método `run` para ejecutar queries SQL.
    schema : str
        Esquema donde se creará la tabla.
    table_name : str
        Nombre de la tabla.
    format : dict[str, str]
        Diccionario con columnas y tipos de datos SQL.
    if_not_exists : bool, default=True
        Si True, agrega cláusula IF NOT EXISTS.
    foreign_keys : dict[str, str], optional
        Diccionario de llaves foráneas en formato
        {columna: referencia}.

    Notes
    -----
    Las columnas se crean con comillas dobles para preservar mayúsculas/minúsculas.
    """
    cols = ", ".join(
        f'"{col}" {dtype}' for col, dtype in format.items()
    )

    constraints = []

    if foreign_keys:
        constraints.extend(
            f'FOREIGN KEY ("{col}") REFERENCES {ref}'
            for col, ref in foreign_keys.items()
        )

    all_defs = ", ".join([cols] + constraints)

    query = f"""
        CREATE TABLE {"IF NOT EXISTS" if if_not_exists else ""}
        {schema}.{table_name} (
            {all_defs}
        );
    """

    hook.run(query)

def replace_table(hook, schema: str, table_name: str, format: dict[str, str], df: pd.DataFrame):
    """
    Reemplaza completamente una tabla por una nueva versión con datos.

    Parameters
    ----------
    hook : object
        Objeto con acceso a la base de datos.
    schema : str
        Esquema de la tabla.
    table_name : str
        Nombre de la tabla.
    format : dict[str, str]
        Definición de columnas y tipos SQL.
    df : pandas.DataFrame
        Datos que reemplazarán el contenido de la tabla.

    Notes
    -----
    Elimina la tabla si existe, la recrea y carga los datos desde el DataFrame.
    """
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
    """
    Inserta o actualiza registros en una tabla SQL (UPSERT).

    Parameters
    ----------
    hook : object
        Objeto con conexión a la base de datos.
    schema : str
        Esquema de la tabla.
    table_name : str
        Nombre de la tabla.
    df : pandas.DataFrame
        Datos a insertar o actualizar.
    key_columns : list of str
        Columnas que definen la clave única para conflictos.

    Returns
    -------
    None

    Raises
    ------
    ValueError
        Si todas las columnas del DataFrame son claves y no hay campos para actualizar.

    Notes
    -----
    Utiliza `ON CONFLICT DO UPDATE` para resolver duplicados.
    """
    conn = hook.get_conn()

    cols = [f'"{c}"' for c in list(df.columns) ]

    key_columns_quoted = [f'"{c}"' for c in key_columns]

    update_cols = [c for c in cols if c not in key_columns_quoted]
    
    if not update_cols:
        raise ValueError(
            f"No columns to update in {schema}.{table_name}. "
            f"All columns are keys: {key_columns}"
        )

    query = f"""
        INSERT INTO {schema}.{table_name} ({", ".join(cols)})
        VALUES ({", ".join(["%s"] * len(cols))})
        ON CONFLICT ({", ".join(key_columns_quoted)})
        DO UPDATE SET {", ".join(
            f"{c}=EXCLUDED.{c}" for c in update_cols
        )}
    """

    with conn.cursor() as cur:
        cur.executemany(query, df.values.tolist())

    conn.commit()