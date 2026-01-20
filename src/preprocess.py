import os
import pandas as pd
import json
from src.data_loader import get_usd_rate_time_series,load_categories,load_products,load_invoices,load_product_codes
import streamlit as st


def get_existence(existences:str)->int:
    global_existence = 0
    existences_clean = existences.replace('nan', 'null')
    existence_data = json.loads(existences_clean)
    for branch in existence_data:
        existencia = branch.get("existencia")
        if existencia is None:
            existencia = 0
        global_existence += existencia
       
    return global_existence

def clean_data()->pd.DataFrame:
    """
    Función que carga datos y los limpia y prepara para el procesamiento.

    """
    # Carga

    invoices = load_invoices()
    product_codes =load_product_codes()
    exchange_rates = get_usd_rate_time_series()
    branches = pd.read_csv("data/raw/almacen.csv")
    
    # Normalizar precios a MXN
    df = invoices.merge(product_codes[["productId","sell_coin","buy_coin","cost"]],how="inner",on="productId")
    df = df.merge(exchange_rates,how="inner",on="date")

    
    df["price"] = df["price"] * (
        1 - df["sell_coin"] + df["exchange_rate"] * df["sell_coin"]
    )
    df["cost"] = df["cost"] * (
        1 - df["buy_coin"] + df["exchange_rate"] * df["buy_coin"]
    )
    df= df.drop(columns=["sell_coin","buy_coin","exchange_rate"])

    # Filtros
    is_sale= (df["quantity"] > 0)&( df["price"] > 0 ) # Solo nos interesan casos donde sí hubo venta
    is_hardware = df["cost"] > 0
    df = df[is_sale & is_hardware]

    # Sucursales
    df['branchId']= df['folio'].str.extract( r'(?P<branchId>[A-Za-z]+)' )
    df = df.merge(branches[["nemonico","sucursal","homoclave"]],how="inner",left_on="branchId",right_on="homoclave")
    
    return df

@st.cache_data
def process_data(update:bool=False)->pd.DataFrame:
    """
    Agarra el dataset limpio y listo para procesar para generar las variables 
    útiles/relevantes en el dashboard. 

    """
    existence= pd.read_csv("data/raw/existencia.csv")
    existence["almacenes"] = existence["almacenes"].str.replace("'", '"')
    existence["total_stock"] =  existence["almacenes"].apply(lambda x: get_existence(x) )

    is_active = existence["activo"]
    exists = existence["total_stock"]!= 0

    existence = existence[is_active & exists]

    columns=["codigo","activo","existencia","total_stock","fechaRegistro"]
    existence = existence[columns]

    

    data_exists= os.path.exists("data/processed/facturas_ventas.parquet")
    if (data_exists)&(not update):
        df=pd.read_parquet("data/processed/facturas_ventas.parquet")
        return df
    else:
        categories = load_categories()
        products = load_products()

        products = products.merge(categories,how="left",on="idCategoria")
        products = products [["clave","nombre"]]

        df = clean_data()

        # Columna de estados
        with open("states_dict.json", "r", encoding="utf-8") as f:
            states_dict = json.load(f)

        df["state"] = df["sucursal"].map(states_dict).fillna("UNKNOWN")

        # Categorías
        df = df.merge(products,how="left",left_on="productId",right_on="clave")
        df = df.rename(columns={"nombre":"category"})

        # Existencia
        df = df.merge(existence,how="inner",left_on="productId",right_on="codigo")
        df.to_parquet('data/processed/facturas_ventas.parquet',index=False)

    return df