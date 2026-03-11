import os
import pandas as pd
import json
import datetime
import numpy as np
import logging

from dashboard.utils import time_period
from pathlib import Path

Date = datetime.datetime
Document =  dict[str, any]
Documents = list[Document]
DATA_PATH = Path('data')


def fill_exchange_rates(rates_dataframe:pd.DataFrame)->pd.DataFrame:
    """
    Rellena valores faltantes en tabla de conversiones de moneda USD a MXN imputando 
    el valor promedio de los ultimos dos valores antes de la conversión faltante. 

    Parametros:
    - rates_dataframe: pandas.DataFrame , Tabla de conversiones de moneda a rellenar

    Regresa:
    - df: pandas.DataFrame, Tabla imputada de conversiones de moneda
    """
    df = rates_dataframe.copy()
    for idx,row in df.iterrows():
        rate = row["exchange_rate"]
        if pd.isna(rate):
            # Principio
            if idx == 0:
                next_idx = idx+1
                rate = df["exchange_rate"].iloc[next_idx]
                while np.isnan(rate):
                    next_idx+=1
                    rate = df["exchange_rate"].iloc[next_idx]
                df["exchange_rate"].iloc[0] = rate
                continue
            if idx == 1:
                df["exchange_rate"].iloc[1] = df["exchange_rate"].iloc[0]
                continue

            fill_rate = np.mean([ df["exchange_rate"].iloc[idx-1], df["exchange_rate"].iloc[idx-2] ]) 
            df["exchange_rate"].iloc[idx] = fill_rate
    return df


def process_exchange_rates(data: pd.DataFrame,raw_rates: pd.DataFrame,start_date: Date = Date(2020,1,1),logger: logging.Logger | None = None
):
    """

    Parametros:
    - data: pandas.DataFrame, Conversiones de moneda historicas 
    - raw_rates: pandas.DataFrame, Tabla de conversiones de moneda extraídas de API 
    - start_date: Date, Fecha de inicio de conversiones de moneda
    - logger: logging.Logger,  Objeto de logeo para capturar información relevante al proceso

    Regresa:
    - : None, 
    """

    if logger:
        logger.info("Actualizando conversiones...")
        print("Actualizando conversiones...")
    else:
        print("Actualizando conversiones...")

    df = data.copy()

    # asegurar formato datetime
    
    df.index = pd.to_datetime(df.index)
    raw_rates = raw_rates.copy()
    raw_rates.index = pd.to_datetime(raw_rates.index)

    # generar periodo completo
    period = pd.DataFrame({
        "date": pd.date_range(start=start_date, end=pd.Timestamp.today(), freq="D")
    })

    merged = (
        period
        .merge(df, how="left", on="date")
        .merge(
            raw_rates.reset_index(),
            how="left",
            on="date",
            suffixes=("", "_fill")
        )
    )

    merged["exchange_rate"] = merged["exchange_rate"].fillna(
        merged["exchange_rate_fill"]
    )

    merged = merged.drop(columns=["exchange_rate_fill"])

    processed_rates = fill_exchange_rates(rates_dataframe=merged)
    processed_rates = processed_rates.set_index("date")

    os.makedirs(DATA_PATH / "processed", exist_ok=True)

    tmp_path = DATA_PATH / "processed" / "conversion_usd_mxn_tmp.parquet"
    final_path = DATA_PATH / "processed" / "conversion_usd_mxn.parquet"

    processed_rates.to_parquet(tmp_path)
    os.replace(tmp_path, final_path)

    if logger:
        logger.info("Actualización realizada correctamente!")
    else:
        print("Actualización realizada correctamente!")

    
   
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

def process_data(invoices:pd.DataFrame,product_codes:pd.DataFrame,exchange_rates:pd.DataFrame,branches:pd.DataFrame,products:pd.DataFrame,categories:pd.DataFrame):
    """
    Agarra el dataset limpio y listo para procesar para generar las variables 
    útiles/relevantes en el dashboard.

    Parametros:
    - invoices: pandas.DataFrame, Datos de facturas
    - product_codes: pandas.DataFrame, Datos de productos, costo y monedas
    - exchange_rates: pandas.DataFrame, Datos de conversión de monedas USD a MXN
    - branches: pandas.DataFrame, Datos de sucursales y almacenes
    - products: pandas.DataFrame, Datos descriptivos de productos. (ej. Categoría, nombre etc.)
    - categories: pandas.DataFrame , Datos de categorías de productos

    Regresa:
    - : None, 

    """
    file_path = DATA_PATH/'processed'/'facturas_ventas.parquet'

    df = invoices.merge(product_codes,
                        how="inner",on="productId")
    df = df.merge(exchange_rates,
                  how="inner",on="date")
        
    df = normalize_coins(df)
    df = sales_filters(df)

    df['branchId']= df['folio'].str.extract( r'(?P<branchId>[A-Za-z]+)' )
    df = df.merge(branches[["storageId","branch","homoclave"]],
                  how="inner",left_on="branchId",right_on="homoclave")
    
    products = products.merge(categories,
                              how="left",on="idCategoria")
    products = products [["clave","nombre"]]


    # Columna de estados
    with open("states_dict.json", "r", encoding="utf-8") as f:
            states_dict = json.load(f)
    df["state"] = df["branch"].map(states_dict).fillna("UNKNOWN")

    # Categorías
    df = df.merge(products,
                      how="left",left_on="productId",right_on="clave")
    df = df.rename(columns={"nombre":"category"})
    df['date']=df['date'].astype('datetime64[ns]')


    os.makedirs(DATA_PATH/'processed',exist_ok=True)
    df = df.drop_duplicates(subset=['folio','productId','date','clientId'])
    df.to_parquet(DATA_PATH/'processed'/'facturas_ventas_tmp.parquet',index=False)
    os.replace(DATA_PATH/'processed'/'facturas_ventas_tmp.parquet', file_path)
        