import os
import pandas as pd
import json
from src.data_loader import get_query,load_data
import numpy as np
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
    # Limpieza / Filtros

    invoices,categories,products,product_codes= load_data(output_file="data/facturas.parquet",file_format="parquet")
    branches = pd.read_csv("data/almacen.csv")
    branches = branches[["nemonico","sucursal","homoclave"]]


    invoices['SUCURSAL']= invoices['folio'].str.extract( r'(?P<SUCURSAL>[A-Za-z]+)' )
    
    product_codes = product_codes.astype({'PRODUCTO':'string'}) 
    invoices = invoices.merge(product_codes, left_on="productId",right_on='PRODUCTO', how='inner')

    is_sale= (invoices["quantity"] > 0)&( invoices["price"] > 0 ) # Solo nos interesan casos donde sí hubo venta
    is_hardware = invoices["ART_COS"] > 0
    invoices = invoices[is_sale & is_hardware]

    invoices = invoices.merge(branches,how="inner",left_on="SUCURSAL",right_on="homoclave")
    
    return invoices

@st.cache_data
def process_data(update:bool=False)->pd.DataFrame:
    """
    Agarra el dataset limpio y listo para procesar para generar las variables 
    útiles/relevantes en el dashboard. 

    """
    existence= pd.read_csv("data/existencia.csv")
    existence["almacenes"] = existence["almacenes"].str.replace("'", '"')
    existence["total_stock"] =  existence["almacenes"].apply(lambda x: get_existence(x) )

    is_active = existence["activo"]
    exists = existence["total_stock"]!= 0

    existence = existence[is_active & exists]

    columns=["codigo","activo","existencia","total_stock","fechaRegistro"]
    existence = existence[columns]

    

    data_exists= os.path.exists("data/processed.parquet")
    if (data_exists)&(not update):
        df=pd.read_parquet("data/processed.parquet")
        return df
    else:
        categories = pd.read_parquet("data/categorias.parquet")
        products = pd.read_parquet("data/productos.parquet")

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
        
        df = df.rename(columns={"ART_COS":"cost"})
        df.to_parquet('data/processed.parquet',index=False)

    return df