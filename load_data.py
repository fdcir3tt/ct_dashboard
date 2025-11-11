import os
import json
import pyodbc
import argparse
import pyarrow.parquet as pq
import pyarrow as pa
import pandas as pd
from dotenv import load_dotenv
import tempfile
import shutil
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

## Columnas

table_name=os.getenv("SALES_TABLE_NAME")
date_col=os.getenv("DATE_COLUMN")
schema=os.getenv("DB_SCHEMA")
data_columns=os.getenv("SALES_DATA_COLUMNS")
sales_art_col=os.getenv("SALES_ARTICLE_COLUMN")
price_col=os.getenv("SALES_PRICE")

def get_query(query:str,connection_str:str)->pd.DataFrame:    
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
                          temp_dir:str,**kwargs):
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

        # Guardar último offset
        save_last_processed_offset(offset_file, n_rows)
        print(f" Extracción completada. Archivo guardado en: {output_file}")

        shutil.rmtree(temp_dir)
        print(f" Archivos temporales eliminados: {temp_dir}")

    except Exception as e:
        print(f" Error crítico: {e}")







if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extraer tabla en paralelo y guardarla en un archivo CSV.")
    parser.add_argument('--output_file', type=str, required=True, help='Ruta de archivo CSV final ')
    parser.add_argument('--connection_str', type=str, default=conn_str, help='String de conexión')
    parser.add_argument('--chunk_percent', type=float, default=10.0, help='Porcentaje de tabla a extraer por chunk')
    parser.add_argument('--table_name', type=str, default=table_name, help='Nombre de tabla extraída')
    parser.add_argument('--schema', type=str, default='dbo', help='Esquema de base de datos')
    parser.add_argument('--order_column', type=str, default=date_col, help='Columna fecha utilizada para ordenamiento en consulta')
    parser.add_argument('--offset_file', type=str, default='last_offset.json', help='Archivo en el cual se guarda último offset')
    parser.add_argument('--max_workers', type=int, default=4, help='Number of threads to use')
    parser.add_argument('--start_date', type=int, required=True, help='Fecha inicio de periodo de ventas')
    parser.add_argument('--end_date', type=int, required=True, help='Fecha final de periodo de ventas')

    args = parser.parse_args()

    query = f"""
            SELECT {data_columns}
            FROM {schema}.{table_name}
            WHERE {date_col} BETWEEN '{args.start_date}' AND '{args.end_date}'
            AND {price_col} > 0 

    """

    extract_table_parallel(
        query=query,
        output_file=args.output_file,
        connection_str=args.connection_str,
        chunk_percent=args.chunk_percent,
        table_name=args.table_name,
        schema=args.schema,
        order_column=args.order_column,
        offset_file=args.offset_file,
        max_workers=args.max_workers
    )