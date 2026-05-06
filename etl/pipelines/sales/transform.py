import pandas as pd
import hashlib

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
    extracted_invoice_documents = pd.DataFrame(context["ti"].xcom_pull(task_ids="extract_rates_branches_products_and_categories", key="extracted_invoice_documents"))
    products_info               = pd.DataFrame(context["ti"].xcom_pull(task_ids="extract_rates_branches_products_and_categories", key="products_info"))
    exchange_rates              = pd.DataFrame(context["ti"].xcom_pull(task_ids="extract_rates_branches_products_and_categories", key="exchange_rates"))
    branches                    = pd.DataFrame(context["ti"].xcom_pull(task_ids="extract_rates_branches_products_and_categories", key="branches"))
    categories                  = pd.DataFrame(context["ti"].xcom_pull(task_ids="extract_rates_branches_products_and_categories", key="categories"))
    
    transformed_data = transform(extracted_invoice_documents,products_info,exchange_rates,branches,categories)
    
    context["ti"].xcom_push(key="sales_invoices", value=transformed_data.to_dict(orient="records"))