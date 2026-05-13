import os
import requests
import zipfile
import geopandas as gpd

from airflow import DAG
from pathlib import Path
from dotenv import load_dotenv
from datetime import timedelta

from common.paths import DATA_DIR,ENV_DIR
from psycopg2.extras import execute_values

from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook

load_dotenv(ENV_DIR)

# -----------------------------------------------------------
# SETUP
# -----------------------------------------------------------
zip_url = "https://geodata.ucdavis.edu/gadm/gadm4.1/shp/gadm41_MEX_shp.zip"
conn_str="dashboard_app_db"
conn_uri = os.getenv("AIRFLOW__DATABASE__SQL_ALCHEMY_CONN")
download_dir = DATA_DIR / "raw"
zip_path = download_dir / "gadm41_MEX_shp.zip"
extract_dir = download_dir / "gadm41_MEX_shp"

download_dir.mkdir(parents=True, exist_ok=True)
extract_dir.mkdir(parents=True, exist_ok=True)


def upload_mexico_shp()->gpd.GeoDataFrame:
    """
    Carga archivos 'shp' necesarios de México para mapa de calor
    """
    mexico = gpd.read_file("data/raw/gadm41_MEX_shp/gadm41_MEX_1.shp")
    mexico["geometry"] = mexico["geometry"].simplify(
        tolerance=0.01, preserve_topology=True
    )
    mexico["state"] = mexico["NAME_1"].str.upper()
    return mexico[["state","geometry"]]

def extract(zip_url:str,path:Path)->dict[str,str]:

    with requests.get(zip_url, stream=True) as r:
        r.raise_for_status()
        with open(path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

    print("Download complete.")
    return {"zip_path":str(path)}

def transform(path:Path,extraction_dir:Path)->gpd.GeoDataFrame:
    with zipfile.ZipFile(path, "r") as zip_ref:
        zip_ref.extractall(extraction_dir)

    print("Extraction complete.")


    path.unlink()
    print("ZIP file deleted.")

    geometries = upload_mexico_shp()
    
    return geometries

def load(geometries: gpd.GeoDataFrame, conn_str: str):
    hook = PostgresHook(postgres_conn_id=conn_str)

    table_exists = hook.get_first("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'raw'
            AND table_name = 'geometrias'
        )
    """)[0]

    if table_exists:
        has_data = hook.get_first("SELECT 1 FROM raw.geometrias LIMIT 1")
        if has_data:
            print("Data already exists, skipping load.")
            return

    print("Creando tabla de geometrías estatales...")

    conn = hook.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS raw.geometrias (
                    state TEXT PRIMARY KEY,
                    geometry geometry(MULTIPOLYGON, 4326)
                );
            """)

            rows = [
                (row.state, row.geometry.wkb_hex)
                for row in geometries.itertuples(index=False)
            ]

            execute_values(cur, """
                INSERT INTO raw.geometrias (state, geometry)
                VALUES %s
            """, rows, template="(%s, ST_GeomFromWKB(decode(%s, 'hex'), 4326))")

        conn.commit()
    finally:
        conn.close()
    
    

def run_extract(**context):
    extracted_data = extract(zip_url,zip_path)
    context["ti"].xcom_push(key="zip_path", value=extracted_data)
    
def run_transform(**context):
    zip_path = Path(context["ti"].xcom_pull(task_ids="extract_shapefile_zip", key="zip_path")["zip_path"])
    transformed_data = transform(zip_path,extract_dir)
    output_path = DATA_DIR/"geometries.parquet"
    transformed_data.to_parquet(output_path, engine="pyarrow")
    return str(output_path)

def run_load(**context):
    file_path = Path( context["ti"].xcom_pull(task_ids="decompress_and_delete_zip_file", key="return_value"))
    geometries = gpd.read_parquet(file_path)
    
    geometries = gpd.GeoDataFrame(geometries, geometry="geometry",crs="EPSG:4326")

    load(geometries,conn_str)
    file_path.unlink()
    


#  Configuración del DAG
default_args = {
    "owner": "Federico",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}

with DAG(
    dag_id="mexico_shapefile_extraction",
    default_args=default_args,
    description="Script de extracción de datos geográficos de México ",
    schedule=None,  # Manual
    catchup=False,
    tags=["raw"],
) as dag:

    extract_task = PythonOperator(
        task_id="extract_shapefile_zip",
        python_callable=run_extract,
    )

    transform_task = PythonOperator(
        task_id="decompress_and_delete_zip_file",
        python_callable=run_transform,
    )

    load_task = PythonOperator(
        task_id="load_geometries",
        python_callable=run_load,
    )

    
    extract_task >> transform_task >> load_task