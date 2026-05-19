import pandas as pd

from typing import Any
from common.registry import register
from airflow.exceptions import AirflowFailException

save_dict = {"invoice_documents":"sales_invoices_df"}
tag = "sales"

def normalize_coins(df:pd.DataFrame)->pd.DataFrame:
    """
    Estandariza columnas de precio y costo a MXN

    Parametros:
    - df: pandas.DataFrame, Datos de facturas a estandárizar
    Regresa:
    - df: pandas.DataFrame, Datos estandarizados a moneda MXN
    """

    df["total"] = df["total"] * (
        1 - df["sell_coin"] + df["exchange_rate"] * df["sell_coin"]
    )
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


@register(tag)
def transform_invoice_documents(extracted_data:dict[str,pd.DataFrame|list[dict[str,Any]]],**kwargs)->pd.DataFrame:
    input_data =["invoice_documents","products_info","exchange_rates"]
    for name in input_data:
        if (name not in extracted_data.keys()):
            raise AirflowFailException(f"Task failed,no data to transform:'{name}' ")
    
    extracted_invoice_documents = extracted_data["invoice_documents"]
    exchange_rates              = extracted_data["exchange_rates"]
    products_info               = extracted_data["products_info"]


    invoices = pd.DataFrame(extracted_invoice_documents)
    invoices = (invoices.rename(columns={"articulo" :"product_id",
                                         "factura"  :"folio",
                                         "cantidad" :"quantity",
                                         "fecha"    :"date",
                                         "precio"   :"price",
                                         "cliente"  :"client_id",
                                         "almacen"  :"sale_storage_id",
                                         })
                        
                        .astype(dtype={"product_id" :"str",
                                       "folio"      :"str",
                                       "quantity"   :"int",
                                       "client_id"  :"str",
                                       "total"      :"float",
                                       })
                         )

    invoices["date"]=pd.to_datetime(invoices["date"])
    invoices["date"]=invoices["date"].dt.date
    sales_invoices_df = invoices.merge(products_info,
                        how="inner",on="product_id")
    sales_invoices_df = sales_invoices_df.drop(columns=["category_id"])
    sales_invoices_df = sales_invoices_df.merge(exchange_rates,
                  how="inner",on="date")
    
    sales_invoices_df = normalize_coins(sales_invoices_df)

    sales_invoices_df = sales_filters(sales_invoices_df)

    sales_invoices_df['date'] = sales_invoices_df['date'].astype('datetime64[ns]')

    sales_invoices_df = sales_invoices_df.drop_duplicates(subset=['folio','product_id','date','client_id'])
    
      
    sales_invoices_df["date"] = sales_invoices_df["date"].dt.date
    
    return sales_invoices_df



    
    