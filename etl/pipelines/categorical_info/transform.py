import os
import pandas as pd

from typing import Any
from dotenv import load_dotenv
from common.paths import ENV_DIR
from common.data import save_data,load_data,generate_tmp_path_strings

env_path = ENV_DIR /".env"
load_dotenv(env_path)

product_columns        = os.getenv("PRODUCT_COLUMNS")
product_code_col       = product_columns.split(',')[0]
product_desc_col       = product_columns.split(',')[1]
product_cost_col       = product_columns.split(',')[2]
product_cost_coin_col  = product_columns.split(',')[3]
product_price_coin_col = product_columns.split(',')[4]

def transform(data:dict[str,list[dict[str,Any]]])->dict[str,pd.DataFrame]:
    transformed_data = {}
    print("Creando dataframes...")
    # Dataframes
    product_catalogue_df = pd.DataFrame(data["product_catalogue_rows"])
    category_df          = pd.DataFrame(data["product_category_rows"])
    client_df            = pd.DataFrame(data["client_list"])
    product_codes_df     = pd.DataFrame(data["product_codes"])
    branches_df          = pd.DataFrame(data["branch_docs"])
    
    print("Renombrando columnas...")

    product_codes_df = (product_codes_df.rename(columns={product_code_col:'product_id',
                                                        product_desc_col:'description',
                                                        product_cost_col:'cost',
                                                        product_cost_coin_col:'buy_coin',
                                                        product_price_coin_col:'sell_coin'})
                                        .astype(dtype={"cost":"float"}))
    branches_df = (branches_df.astype(dtype={'nemonico' :'str',
                                             'sucursal' :'str',
                                             'homoclave':'str'})

                              .rename(columns={'nemonico' :'storage_id',
                                               'homoclave':'branch_id',
                                               'sucursal' :'branch'})
        )
    print("Uniendo dataframes necesarias...")
    # Merging
    product_codes_df = product_codes_df.merge(product_catalogue_df,how="left",on="product_id")
    
    product_codes_df["category_id"] = product_codes_df["category_id"].fillna(99999).astype(dtype="int")
    
    # Agregación
    unknown_cat_df = pd.DataFrame([{"category_id":99999,"parent_id":0,"category":"desconocido"}])
    category_df = pd.concat([category_df,unknown_cat_df])


    transformed_data["category_df"]      = category_df
    transformed_data["client_df"]        = client_df
    transformed_data["product_codes_df"] = product_codes_df
    transformed_data["branches_df"]      = branches_df

    return transformed_data

def run_transform(**context):
    extracted_path_strings = context["ti"].xcom_pull(task_ids="extract_categories_and_products", key="path_strings")
    extracted_data = load_data(extracted_path_strings)

    transformed_data = transform(extracted_data)
    
    path_strings = generate_tmp_path_strings(transformed_data)
    save_data(transformed_data,path_strings)
    
    print("Pasando datos a siguiente proceso...")
    context["ti"].xcom_push(key="path_strings",value=path_strings)
    