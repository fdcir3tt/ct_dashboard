import os
import pandas as pd
import json 

from typing import Callable
from dotenv import load_dotenv
from common.paths import ENV_DIR
from common.data import save_data,load_data,generate_tmp_path_strings

from airflow.exceptions import AirflowSkipException

env_path = ENV_DIR /".env"
load_dotenv(env_path)

product_columns        = os.getenv("PRODUCT_COLUMNS")
product_code_col       = product_columns.split(',')[0]
product_desc_col       = product_columns.split(',')[1]
product_cost_col       = product_columns.split(',')[2]
product_cost_coin_col  = product_columns.split(',')[3]
product_price_coin_col = product_columns.split(',')[4]

save_dict = {"product_category_rows":"categories_df",
             "product_codes"        :"product_codes_df",
             "client_data"          :"clients_df",
             "branch_docs"          :"branches_df"}

def transform_product_codes(product_catalogue_df:pd.DataFrame,product_codes_df:pd.DataFrame)->pd.DataFrame:
    product_codes_df = (product_codes_df.rename(columns={product_code_col:'product_id',
                                                        product_desc_col:'description',
                                                        product_cost_col:'cost',
                                                        product_cost_coin_col:'buy_coin',
                                                        product_price_coin_col:'sell_coin'})
                                        .astype(dtype={"cost":"float"}))
    product_codes_df = product_codes_df.merge(product_catalogue_df,how="left",on="product_id")
    product_codes_df["category_id"] = product_codes_df["category_id"].fillna(99999).astype(dtype="int")
    
    return product_codes_df


def transform_product_category_rows(category_df:pd.DataFrame)->pd.DataFrame:
    unknown_cat_df = pd.DataFrame([{"category_id":99999,"parent_id":0,"category":"desconocido"}])
    category_df = pd.concat([category_df,unknown_cat_df])
    return category_df

def transform_client_data(clients_df:pd.DataFrame)->pd.DataFrame:
     return clients_df

def transform_branch_docs(branches_df:pd.DataFrame)->pd.DataFrame:
    branches_df = (branches_df.astype(dtype={'nemonico' :'str',
                                             'sucursal' :'str',
                                             'homoclave':'str'})

                              .rename(columns={'nemonico' :'storage_id',
                                               'homoclave':'branch_id',
                                               'sucursal' :'branch'})
        )
    with open("states_dict.json", "r", encoding="utf-8") as f:
            states_dict = json.load(f)

    branches_df["state"] = branches_df["branch"].map(states_dict).fillna("UNKNOWN")

    return branches_df
     


def run_transform(transform_fn:Callable,**context):
    extracted_path_strings = context["ti"].xcom_pull(task_ids="gather_extracted_paths", key="path_strings")
    extracted_data = load_data(extracted_path_strings)
    
    
    extracted_data_name = transform_fn.__name__.split("transform_")[1]
    
    if extracted_data_name=="product_codes":
        not_extracted = ("product_catalogue_rows" not in extracted_data.keys() ) and ("product_codes_data" not in extracted_data.keys())
        if not_extracted:
            raise AirflowSkipException(f"Skipping task,missing data:{extracted_data_name.replace("_"," ")} ")

        product_catalogue_df = pd.DataFrame(extracted_data["product_catalogue_rows"])
        product_codes_df = pd.DataFrame(extracted_data["product_codes_data"])
        transformed_data = transform_fn(product_catalogue_df,product_codes_df)
    else:
        not_extracted = extracted_data_name not in extracted_data.keys()
        if not_extracted:
            raise AirflowSkipException(f"Skipping task,missing data:{extracted_data_name.replace("_"," ")} ")

        extracted_df = pd.DataFrame(extracted_data[extracted_data_name])
        transformed_data = transform_fn(extracted_df)
    
    path_string = generate_tmp_path_strings({save_dict[extracted_data_name]:transformed_data})[0]
    
    save_data(transformed_data,path_string)
    
    context["ti"].xcom_push(key="path_string",value=path_string)

def gather_transformed_paths(**context):
    upstream_task_ids = context["ti"].task.upstream_task_ids
    gathered_paths = []

    for task_id in upstream_task_ids:
        value = context["ti"].xcom_pull(task_ids=task_id,key="path_string")
        if value is None:
            continue
        gathered_paths.append(value)
    context["ti"].xcom_push(key="path_strings",  value=gathered_paths)
