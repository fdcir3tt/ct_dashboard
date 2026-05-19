import pandas as pd
from common.data import load_data
from common.registry import register
from common.paths import DATA_DIR

raw_data_directory = DATA_DIR/"raw"
extracted_conditions = {"categories"         :"stop",
                        "product_codes"      :"stop",
                        "raw_rates"          :"stop",
                        "extracted_rates"    :"stop",
                         }
tag = "migration"

@register(tag)
def extract_categories(**kwargs)->pd.DataFrame:
    file_path  = raw_data_directory/"categorias.parquet"
    categories = load_data(file_path)
    return categories

@register(tag)
def extract_product_codes(**kwargs)->pd.DataFrame:
    file_path     = raw_data_directory/"catalogo_productos.parquet"
    product_codes = load_data(file_path)
    return product_codes

@register(tag)
def extract_raw_rates(**kwargs)->pd.DataFrame:
    file_path = raw_data_directory/"historical_data_usd_mxn_2008-12-31_to_2026-01-20.csv"
    raw_rates = load_data(file_path)
    return raw_rates
@register(tag)
def extract_extracted_rates(**kwargs)->pd.DataFrame:
    file_path       = raw_data_directory/"usd_mxn_rates.parquet"
    extracted_rates = load_data(file_path)
    return extracted_rates

