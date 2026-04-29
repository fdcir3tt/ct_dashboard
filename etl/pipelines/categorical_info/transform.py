import os
import pandas as pd

from typing import Any
from dotenv import load_dotenv
from common.paths import ENV_DIR

env_path = ENV_DIR /".env"
load_dotenv(env_path)

product_columns = os.getenv("PRODUCT_COLUMNS")
product_code_col= product_columns.split(',')[0]
product_desc_col= product_columns.split(',')[1]
product_cost_col= product_columns.split(',')[2]
product_cost_coin_col= product_columns.split(',')[3]
product_price_coin_col= product_columns.split(',')[4]

def transform(product_catalogue_rows:list[dict[str,Any]],product_category_rows:list[dict[str,Any]],client_list:list[dict[str,Any]],product_codes:list[dict[str,Any]]):
    print("Creando dataframes...")
    # Dataframes
    product_catalogue_df = pd.DataFrame(product_catalogue_rows)
    category_df = pd.DataFrame(product_category_rows)
    client_df = pd.DataFrame(client_list)
    product_codes_df = pd.DataFrame(product_codes)

    print("Uniendo dataframes necesarias...")
    # Merging
    category_df = product_catalogue_df.merge(category_df,how="left",on="idCategoria")
    
    print("Renombrando columnas...")
    # Renombrar columnas
    category_df = category_df[["clave","nombre"]].rename(columns={"clave":"productId",
                                                                  "nombre":"category"})
    
    client_df = client_df.rename(columns={os.getenv("ID_COLUMN"):"clientId",
                                          os.getenv("CITY_COLUMN"):"city"})

    product_codes_df = product_codes_df.rename(columns={product_code_col:'productId',
                                                        product_desc_col:'description',
                                                        product_cost_col:'cost',
                                                        product_cost_coin_col:'buy_coin',
                                                        product_price_coin_col:'sell_coin'})
    return category_df,client_df,product_codes_df

def run_transform(**context):
    product_catalogue_rows= context["ti"].xcom_pull(task_ids="extract", key="product_catalogue_rows")
    product_category_rows= context["ti"].xcom_pull(task_ids="extract", key="product_category_rows")
    client_list= context["ti"].xcom_pull(task_ids="extract", key="client_list")
    product_codes= context["ti"].xcom_pull(task_ids="extract", key="product_codes")

    transformed_data = transform(product_catalogue_rows,product_category_rows,client_list,product_codes)
    print("Pasando datos a siguiente proceso...")
    context["ti"].xcom_push(key="category_df", value=transformed_data[0].to_dict(orient="records"))
    context["ti"].xcom_push(key="client_df", value=transformed_data[1].to_dict(orient="records"))
    context["ti"].xcom_push(key="product_codes_df", value=transformed_data[2].to_dict(orient="records"))