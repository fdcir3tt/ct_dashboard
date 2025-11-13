import os
import pandas as pd
import json
from src.data_loader import get_query,load_data



def clean_data()->pd.DataFrame:
    """
    Función que carga datos y los limpia y prepara para el procesamiento.

    """
    # Limpieza / Filtros

    df,categories,products= load_data()

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

    df = df.merge(products, left_on="productId",right_on='PRODUCTO', how='left')

    is_sale= (df["cantidad"] > 0)&( df["price"] > 0 ) # Solo nos interesan casos donde sí hubo venta
    df = df[is_sale]

    branches=['HMO','OBR','LMO','CLN','QRO','TJN','XAL','VER','MAZ','PAZ','MXL','ENS']
    is_branch= df['SUCURSAL'].isin(branches)

    df = df[is_branch]
    return df

def process_data()->pd.DataFrame:
    """
    Agarra el dataset limpio y listo para procesar para generar las variables 
    útiles/relevantes en el dashboard. 

    """
    existence= pd.read_csv("data/existencia.csv")
    branches= pd.read_csv("data/almacen.csv") 

    df = clean_data()
    df["fecha"] = pd.to_datetime(df["fecha"])

    df["month"]=df["fecha"].dt.month
    df["year"]=df["fecha"].dt.year

    # Per-product sales
    df["sales_day"]   = df.groupby(["productId", "fecha"])["cantidad"].transform("sum")
    df["sales_month"] = df.groupby(["productId", "month", "year"])["cantidad"].transform("sum")

    # Frequency of sales entries per product/date
    df["sales_freq"]  = df.groupby(["productId", "fecha"])["cantidad"].transform("count")

    # Profit calculations
    df["profit"] = df["price"] * df["cantidad"]
    df["total_profit"] = df.groupby("productId")["profit"].transform("sum")

    # Category-level sales
    #df["cat_sales_day"]   = df.groupby(["category", "fecha"])["cantidad"].transform("sum")
    #df["cat_sales_month"] = df.groupby(["category", "mes", "año"])["cantidad"].transform("sum")



    df.to_csv('data/processed.csv')

    return df