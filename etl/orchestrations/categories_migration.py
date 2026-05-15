import pandas as pd

from pathlib import Path
from datetime import timedelta

from common.paths import DATA_DIR
from common.data import generate_tmp_path_strings,save_data,load_data
from common.db import create_table, upsert_df

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook



raw_data_path = DATA_DIR/"raw"
conn_str = "dashboard_app_db"

def extract(raw_data_directory:Path)->dict[str,pd.DataFrame]:
    extracted_data = {}
    product_codes = pd.read_parquet(raw_data_directory/"catalogo_productos.parquet",engine="pyarrow")

    categories = pd.read_parquet(raw_data_directory/"categorias.parquet",engine="pyarrow")
    categories = categories.drop(columns=["imagen","slug","fecha"])
    
    raw_rates = pd.read_csv(raw_data_directory/"historical_data_usd_mxn_2008-12-31_to_2026-01-20.csv",sep=";")
    
    extracted_rates = pd.read_parquet(raw_data_directory/"usd_mxn_rates.parquet",engine="pyarrow")
    extracted_rates["date"]=extracted_rates.index
    extracted_rates["date"] = extracted_rates["date"].dt.date

    extracted_data["categories"] = categories
    extracted_data["product_codes"] = product_codes
    extracted_data["raw_rates"] = raw_rates
    extracted_data["extracted_rates"] = extracted_rates

    return extracted_data

def transform(extracted_data:dict[str,pd.DataFrame])->dict[str,pd.DataFrame]:
    categories = extracted_data["categories"]
    raw_rates  = extracted_data["raw_rates"]
    extracted_rates  = extracted_data["extracted_rates"]
    product_codes = extracted_data["product_codes"]

    transformed_data = {}
    raw_rates = raw_rates[["Date","Close"]]
    raw_rates = ( raw_rates .rename(columns={"Date":"date",
                                            "Close":"exchange_rate"})

                            .astype({"exchange_rate":"float"})

                )
    categories = categories.rename(columns={"idCategoria":"category_id",
                                            "idPadre":"parent_id",
                                            "nombre":"category"})
    unknown_cat_df = pd.DataFrame([{"category_id":99999,"parent_id":0,"category":"desconocido"}])
    categories = pd.concat([categories,unknown_cat_df])

    extracted_rates["fallback"]=""

    transformed_data["transformed_categories"] = categories
    transformed_data["transformed_product_codes"] = product_codes
    transformed_data["transformed_raw_rates"] = raw_rates
    transformed_data["transformed_extracted_rates"] = extracted_rates
    

    return transformed_data

def load(transformed_data:dict[str,pd.DataFrame],conn_str):
    transformed_categories = transformed_data["transformed_categories"]
    transformed_raw_rates  = transformed_data["transformed_raw_rates"]
    transformed_extracted_rates  = transformed_data["transformed_extracted_rates"]
    transformed_product_codes = transformed_data["transformed_product_codes"]

    hook = PostgresHook(postgres_conn_id=conn_str)


    create_table(hook,"raw","tazas_historicas",{"date"           :"DATE PRIMARY KEY",
                                                "exchange_rate"  :"NUMERIC"})
    print("Poblando tabla de conversiones USD->MXN de moneda limpias...")
    upsert_df(hook,"raw","tazas_historicas",transformed_raw_rates,["date"])



    create_table(hook,"raw","catalogo_categorias",{"category_id":"Integer PRIMARY KEY",
                                                   "parent_id"  :"Integer",
                                                   "category"   :"VARCHAR"})
    print("Poblando tabla de categorias de productos...")
    upsert_df(hook,"raw","catalogo_categorias",transformed_categories,["category_id"])

    print("Creando tabla de productos...")
    create_table(hook,"raw","catalogo_productos",{"product_id"   :"VARCHAR PRIMARY KEY",
                                                  "category_id"  :"Integer",
                                                  "description" :"TEXT",
                                                  "cost"        :"REAL",
                                                  "buy_coin"    :"Integer",
                                                  "sell_coin"   :"Integer"},foreign_keys={"category_id":'raw.catalogo_categorias("category_id")'})
            
    print("Poblando tabla de productos...")
    upsert_df(hook,"raw","catalogo_productos",transformed_product_codes,key_columns=["product_id"])

    create_table(hook,"raw","tazas_extraidas",{"date"         :"DATE PRIMARY KEY",
                                               "exchange_rate":"NUMERIC",
                                               "fallback"     :"VARCHAR"})
    print("Poblando tabla de tazas extraídas...")
    upsert_df(hook,"raw","tazas_extraidas",transformed_extracted_rates,["date"])


def run_extract(**context):
    extracted_data = extract(raw_data_path)
    extract_path_strings = generate_tmp_path_strings(extracted_data)
    save_data(extracted_data,extract_path_strings)
    context["ti"].xcom_push(key="cat_and_rates_migration_extracted_path_strings", value=extract_path_strings)
    

def run_transform(**context):
    extract_path_strings = context["ti"].xcom_pull(task_ids="extract_historical_data", key="cat_and_rates_migration_extracted_path_strings")
    extracted_data = load_data(extract_path_strings)
    
    transformed_data = transform(extracted_data)
    transform_path_strings = generate_tmp_path_strings(transformed_data)
    save_data(transformed_data,transform_path_strings)
    
    context["ti"].xcom_push(key="cat_and_rates_migration_transformed_path_strings", value = transform_path_strings )
   


def run_load(**context):
    
    extract_path_strings = context["ti"].xcom_pull(task_ids="rename_columns", key="cat_and_rates_migration_transformed_path_strings")
    transformed_data = load_data(extract_path_strings)
    
    
    
    load(transformed_data,conn_str)
    
  

#  Configuración del DAG
default_args = {
    "owner": "Federico",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}

with DAG(
    dag_id="product_category_and_coin_rates_backup",
    default_args=default_args,
    description="Script de migración de datos parquet a tablas SQL",
    schedule=None,  # Manual
    catchup=False,
    tags=["raw"],
) as dag:

    extract_task = PythonOperator(
        task_id="extract_historical_data",
        python_callable=run_extract,
    )
    

    transform_task = PythonOperator(
        task_id="rename_columns",
        python_callable=run_transform,
    )

   

    load_task = PythonOperator(
        task_id="load_historic_data",
        python_callable=run_load,
    )

    trigger_categorical_info_dag = TriggerDagRunOperator(
        task_id="trigger_categorical_info_dag",
        trigger_dag_id="categorical_info",
    )

    trigger_currency_dag = TriggerDagRunOperator(
        task_id="trigger_currency_rates_dag",
        trigger_dag_id="currency_rates",
    )
    
    trigger_shapefile_dag = TriggerDagRunOperator(
        task_id="trigger_shapefile_dag",
        trigger_dag_id="mexico_shapefile_extraction",
    )

    
    [extract_task,trigger_shapefile_dag] >> transform_task >> load_task >>[trigger_categorical_info_dag,trigger_currency_dag]