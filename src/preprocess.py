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

    df = df.merge(products, on='PRODUCTO', how='left')

    is_sale= (df['CANTIDAD'] > 0)&( df['PRECIO'] > 0 ) # Solo nos interesan casos donde sí hubo venta
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
    df = clean_data()
    df["fecha"] = pd.to_datetime(df["fecha"])

    df["mes"]=df["fecha"].dt.month
    df["año"]=df["fecha"].dt.year

    df["sales_day"]= df.groupby(["productId","fecha"])["CANTIDAD"].sum()
    df["sales_month"]= df.groupby(["productId","mes","año"])["CANTIDAD"].sum()
    df["sales_freq"] = df.groupby(["productId","fecha"]).value_counts()

    df["total_profit"]= df.groupby("productId").apply(lambda row:row["price"]*row["cantidad"]).sum()
    df["total_profit"]= df.groupby("productId").apply(lambda row:row["price"]*row["cantidad"]).sum()

    df["cat_sales_day"]= df.groupby(["category","fecha"])["CANTIDAD"].sum()
    df["cat_sales_month"]= df.groupby(["category","mes","año"])["CANTIDAD"].sum()


    df.to_csv('data/processed.csv')
    
    return df