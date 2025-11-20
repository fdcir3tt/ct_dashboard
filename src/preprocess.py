import os
import pandas as pd
import json
from src.data_loader import get_query,load_data
import numpy as np


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

    df,categories,products= load_data()
    branches = pd.read_csv("data/almacen.csv")
    branches = branches[["nemonico","sucursal","homoclave"]]

    # Renombramiento
    name_dict_str= os.getenv('NAME_DICT')
    name_dict = json.loads(name_dict_str)

    # Formatos de columnas
    type_dict_str= os.getenv('TYPE_DICT')
    type_dict = json.loads(type_dict_str)


    df= df.astype(type_dict)
    df= df.rename(columns=name_dict) 

    df['SUCURSAL']= df['FOLIO'].str.extract(r'([A-Za-z]+)')
    products= products.astype({'PRODUCTO':'string'}) 

    df = df.merge(products, left_on="productId",right_on='PRODUCTO', how='inner')

    is_sale= (df["cantidad"] > 0)&( df["price"] > 0 ) # Solo nos interesan casos donde sí hubo venta
    df = df[is_sale]

    df = df.merge(branches,how="inner",left_on="SUCURSAL",right_on="homoclave")
    
    return df

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

    existence = existence[is_active&exists]

    columns=["codigo","activo","existencia","total_stock","fechaRegistro"]
    existence = existence[columns]

    

    data_exists= os.path.exists("data/processed.csv")
    if (data_exists)&(~update):
        df=pd.read_csv("data/processed.csv")
        return df
    else:
        categories = pd.read_parquet("data/categorias.parquet")
        products = pd.read_parquet("data/productos.parquet")

        products = products.merge(categories,how="left",on="idCategoria")
        products = products [["clave","nombre"]]


        branches= pd.read_csv("data/almacen.csv") 

        df = clean_data()
        df["fecha"] = pd.to_datetime(df["fecha"])

        df["month"] = df["fecha"].dt.month
        df["year"] = df["fecha"].dt.year

        # Per-product sales
        df["sales_day"]   = df.groupby(["productId", "fecha"])["cantidad"].transform("sum")
        df["sales_month"] = df.groupby(["productId", "month", "year"])["cantidad"].transform("sum")

        # Frecuencias de ventas diarias 
        df["sales_freq"]  = df.groupby(["productId", "fecha"])["cantidad"].transform("count")

        # Cálculo de ganancias
        df["profit"] = df["price"] * df["cantidad"]
        df["total_profit"] = df.groupby("productId")["profit"].transform("sum")

        # Categorías

        df = df.merge(products,how="left",left_on="productId",right_on="clave")
        df = df.rename(columns={"nombre":"category"})

        # Category-level sales
        df["cat_sales_day"]   = df.groupby(["category", "fecha"])["cantidad"].transform("sum")
        df["cat_sales_month"] = df.groupby(["category", "month", "year"])["cantidad"].transform("sum")

        # Columna de estados
        with open("states_dict.json", "r", encoding="utf-8") as f:
            states_dict = json.load(f)

        df["state"] = df["sucursal"].map(states_dict).fillna("UNKNOWN")
    

        # Existencia
        df = df.merge(existence,how="inner",left_on="productId",right_on="codigo")
        

        
        #n = len(df)
        #df["stock"] = np.linspace(1000, 200, n) + np.random.randint(-20, 20, n)
        df = df.rename(columns={"ART_COS":"cost"})
        df.to_csv('data/processed.csv',index=False)

    return df