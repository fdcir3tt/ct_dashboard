import os
import pandas as pd

from typing import Any
from dotenv import load_dotenv
from common.paths import ENV_DIR

env_path = ENV_DIR /".env"
load_dotenv(env_path)

product_columns        = os.getenv("PRODUCT_COLUMNS")
product_code_col       = product_columns.split(',')[0]
product_desc_col       = product_columns.split(',')[1]
product_cost_col       = product_columns.split(',')[2]
product_cost_coin_col  = product_columns.split(',')[3]
product_price_coin_col = product_columns.split(',')[4]

def transform(product_catalogue_rows:list[dict[str,Any]],product_category_rows:list[dict[str,Any]],client_list:list[dict[str,Any]],product_codes:list[dict[str,Any]],branch_docs:list[dict[str,Any]]):
    print("Creando dataframes...")
    # Dataframes
    product_catalogue_df = pd.DataFrame(product_catalogue_rows)
    category_df          = pd.DataFrame(product_category_rows)
    client_df            = pd.DataFrame(client_list)
    product_codes_df     = pd.DataFrame(product_codes)
    branches_df          = pd.DataFrame(branch_docs)
    
    print("Renombrando columnas...")

    product_codes_df = product_codes_df.rename(columns={product_code_col:'productId',
                                                        product_desc_col:'description',
                                                        product_cost_col:'cost',
                                                        product_cost_coin_col:'buy_coin',
                                                        product_price_coin_col:'sell_coin'})
    
    branches_df = (branches_df.astype(dtype={'nemonico' :'str',
                                             'sucursal' :'str',
                                             'homoclave':'str'})

                              .rename(columns={'nemonico' :'storageId',
                                               'homoclave':'branchId',
                                               'sucursal' :'branch'})
        )
    print("Uniendo dataframes necesarias...")
    # Merging
    product_codes_df = product_codes_df.merge(product_catalogue_df,how="left",on="productId")
    
    product_codes_df["categoryId"] = product_codes_df["categoryId"].fillna("unknown").astype(dtype="str")
    
    return category_df,client_df,product_codes_df,branches_df

def run_transform(**context):
    product_catalogue_rows = context["ti"].xcom_pull(task_ids="extract_categories_and_products", key="product_catalogue_rows")
    product_category_rows  = context["ti"].xcom_pull(task_ids="extract_categories_and_products", key="product_category_rows")
    client_list            = context["ti"].xcom_pull(task_ids="extract_categories_and_products", key="client_list")
    product_codes          = context["ti"].xcom_pull(task_ids="extract_categories_and_products", key="product_codes")
    branch_docs            = context["ti"].xcom_pull(task_ids="extract_categories_and_products", key="branch_docs")

    transformed_data = transform(product_catalogue_rows,product_category_rows,client_list,product_codes,branch_docs)
    print("Pasando datos a siguiente proceso...")
    context["ti"].xcom_push(key="category_df",      value=transformed_data[0].to_dict(orient="records"))
    context["ti"].xcom_push(key="client_df",        value=transformed_data[1].to_dict(orient="records"))
    context["ti"].xcom_push(key="product_codes_df", value=transformed_data[2].to_dict(orient="records"))
    context["ti"].xcom_push(key="branches_df",      value=transformed_data[3].to_dict(orient="records"))