import os
import pandas as pd
import json 


from dotenv import load_dotenv
from common.paths import ENV_DIR
from common.registry import register
from airflow.exceptions import AirflowFailException

env_path = ENV_DIR /".env"
load_dotenv(env_path)

product_columns        = os.getenv("PRODUCT_COLUMNS")
product_code_col       = product_columns.split(',')[0]
product_desc_col       = product_columns.split(',')[1]
product_cost_col       = product_columns.split(',')[2]
product_cost_coin_col  = product_columns.split(',')[3]
product_price_coin_col = product_columns.split(',')[4]

save_dict = {       "product_category_rows":"categories_df"   ,
                    "product_codes_data"   :"product_codes_df",
                    "clients_data"         :"clients_df"      ,
                    "branch_docs"          :"branches_df"     ,
                 }

tag = "categorical_info"
@register(tag)
def transform_product_codes_data(extracted_data:dict[str,pd.DataFrame],**kwargs)->pd.DataFrame:
    
    if ("product_catalogue_rows" not in extracted_data.keys()):
        raise AirflowFailException(f"Task failed,no data to transform:'product_catalogue_rows' ")
    if ("product_codes_data" not in extracted_data.keys()):
        raise AirflowFailException(f"Task failed,no data to transform:'product_codes_data' ")
    
    product_catalogue_df = pd.DataFrame(extracted_data["product_catalogue_rows"])
    product_codes_df     = pd.DataFrame(extracted_data["product_codes_data"])

    product_codes_df     = (product_codes_df.rename(columns={product_code_col:'product_id',
                                                        product_desc_col:'description',
                                                        product_cost_col:'cost',
                                                        product_cost_coin_col:'buy_coin',
                                                        product_price_coin_col:'sell_coin'})
                                        .astype(dtype={"cost":"float"}))
    product_codes_df = product_codes_df.merge(product_catalogue_df,how="left",on="product_id")
    product_codes_df["category_id"] = product_codes_df["category_id"].fillna(99999).astype(dtype="int")
    
    return product_codes_df

@register(tag)
def transform_product_category_rows(extracted_data:dict[str,pd.DataFrame],**kwargs)->pd.DataFrame:
    category_df = pd.DataFrame(extracted_data["product_category_rows"])
    unknown_cat_df = pd.DataFrame([{"category_id":99999,"parent_id":0,"category":"desconocido"}])
    category_df = pd.concat([category_df,unknown_cat_df])
    return category_df

@register(tag)
def transform_clients_data(extracted_data:dict[str,pd.DataFrame])->pd.DataFrame:
    clients_df = pd.DataFrame(extracted_data["clients_data"])
    return clients_df
@register(tag)
def transform_branch_docs(extracted_data:dict[str,pd.DataFrame],**kwargs)->pd.DataFrame:
    branches_df = pd.DataFrame(extracted_data["branch_docs"])
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
     



