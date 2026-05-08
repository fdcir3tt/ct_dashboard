import pandas as pd
import hashlib

from pathlib import Path
from common.data import save_data,load_data,delete_files
from typing import Any

def normalize_coins(df:pd.DataFrame)->pd.DataFrame:
    """
    Estandariza columnas de precio y costo a MXN

    Parametros:
    - df: pandas.DataFrame, Datos de facturas a estandárizar
    Regresa:
    - df: pandas.DataFrame, Datos estandarizados a moneda MXN
    """

    df["price"] = df["price"] * (
        1 - df["sell_coin"] + df["exchange_rate"] * df["sell_coin"]
    )
    df["cost"] = df["cost"] * (
        1 - df["buy_coin"] + df["exchange_rate"] * df["buy_coin"]
    )
    df= df.drop(columns=["sell_coin","buy_coin","exchange_rate"])

    return df


def sales_filters(df:pd.DataFrame)->pd.DataFrame:
    """
    Filtros que determinan si un registro de factura es o no una venta de un producto físico

    Parametros:
    - df: pandas.DataFrame, Datos de facturas a filtrar
    Regresa:
    - df: pandas.DataFrame, Datos filtrados con ventas de productos físicos
    """
    is_sale= (df["quantity"] > 0)&( df["price"] > 0 ) # Solo nos interesan casos donde sí hubo venta
    is_hardware = df["cost"] > 0
    mask = is_sale & is_hardware
    df = df[mask]
    return df


def transform(extracted_invoice_documents:dict[str,Any],products_info:pd.DataFrame,exchange_rates:pd.DataFrame,branches:pd.DataFrame,categories:pd.DataFrame)->pd.DataFrame:
    invoices = pd.DataFrame(extracted_invoice_documents)
    invoices = (invoices.rename(columns={"articulo" :"productId",
                                         "factura" :"folio",
                                         "cantidad":"quantity",
                                         "fecha" :"date",
                                         "cliente" :"clientId",
                                         "descripcion" :"sale_description",
                                         "almacen" :"sale_storageId",
                                         "precio" :"price",})
                        
                        .astype(dtype={"productId":"str",
                                       "folio":"str",
                                       "quantity":"int",
                                       "clientId":"str",
                                       "price":"float",
                                       "total":"float",
                                       })
                         )

    invoices["date"]=pd.to_datetime(invoices["date"])
    invoices["date"]=invoices["date"].dt.date
    df = invoices.merge(products_info,
                        how="inner",on="productId")
    df = df.merge(exchange_rates,
                  how="inner",on="date")
    
    df = normalize_coins(df)

    df = sales_filters(df)

    df['branchId']= df['folio'].str.extract( r'(?P<branchId>[A-Za-z]+)' )

    df = df.merge(branches,
                  how="inner",on="branchId")

    df['date'] = df['date'].astype('datetime64[ns]')

    df = df.drop_duplicates(subset=['folio','productId','date','clientId'])
    

    df["salesId"] = (
    df[["folio", "productId", "date", "clientId"]]
    .fillna("")
    .astype(str)
    .apply(lambda row: "-".join(row.values), axis=1)
    .map(lambda x: hashlib.md5(x.encode()).hexdigest())
)   
    df["date"] = df["date"].dt.date
    return df


def run_transform(**context):
    path_strings = context["ti"].xcom_pull(task_ids="extract_rates_branches_products_and_categories", key="path_strings")
    
    extracted_data = load_data(path_strings)

    extracted_invoice_documents = extracted_data["extracted_invoice_documents"]
    products_info               = extracted_data["products_info"]
    exchange_rates              = extracted_data["exchange_rates"]
    branches                    = extracted_data["branches"]
    categories                  = extracted_data["categories"]
    
    transformed_data = transform(extracted_invoice_documents,products_info,exchange_rates,branches,categories)
    
    sales_path = "/tmp/sales.parquet" 
    save_data(transformed_data,sales_path)
    
    context["ti"].xcom_push(key="sales_invoices_path", value=sales_path)
    
    delete_files(path_strings)