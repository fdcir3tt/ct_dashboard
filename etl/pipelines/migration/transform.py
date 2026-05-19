import pandas as pd
from common.registry import register

save_dict = {       "categories"           :"categories_df"   ,
                    "product_codes"        :"product_codes_df",
                    "raw_rates"            :"raw_rates_df"      ,
                    "extracted_rates"      :"extracted_rates_df"     ,
                 }
tag = "migration"
@register(tag)
def transform_categories(extracted_data:dict[str,pd.DataFrame],**kwargs)->pd.DataFrame:
    categories = extracted_data["categories"]
    categories = categories.drop(columns=["imagen","slug","fecha"])
    categories = categories.rename(columns={"idCategoria":"category_id",
                                            "idPadre":"parent_id",
                                            "nombre":"category"})
    unknown_cat_df = pd.DataFrame([{"category_id":99999,"parent_id":0,"category":"desconocido"}])
    categories_df = pd.concat([categories,unknown_cat_df])

    return categories_df

@register(tag)
def transform_product_codes(extracted_data:dict[str,pd.DataFrame],**kwargs)->pd.DataFrame:
    product_codes_df = extracted_data["product_codes"]
    return product_codes_df

@register(tag)
def transform_raw_rates(extracted_data:dict[str,pd.DataFrame],**kwargs)->pd.DataFrame:
    raw_rates  = extracted_data["raw_rates"]
    raw_rates = raw_rates[["Date","Close"]]
    raw_rates_df = ( raw_rates .rename(columns={"Date":"date",
                                            "Close":"exchange_rate"})

                            .astype({"exchange_rate":"float"})

                )
    return raw_rates_df

@register(tag)
def transform_extracted_rates(extracted_data:dict[str,pd.DataFrame],**kwargs)->pd.DataFrame:
    extracted_rates  = extracted_data["extracted_rates"]
    extracted_rates["date"]=extracted_rates.index
    extracted_rates["date"] = extracted_rates["date"].dt.date
    extracted_rates["fallback"]=""
    extracted_rates_df = extracted_rates
    return extracted_rates_df

