import os
import pandas as pd

from pathlib import Path
from typing import Iterable
from mlops.utils import save_file_safe,time_period,data_dir,Date



def extract(file_name:str)->pd.DataFrame|None:
    """
    Extrae los datos del nombre de archivo específicado

    Parametros:
    -file_name:str, Nombre de archivo que se quiere extraer del directorio 'raw' de datos

    Regresa:
    - df: pandas.DataFrame, Datos cargados de archivo específicado
    """
    file_path = data_dir / 'raw' / file_name
    if file_path.exists():
        df = pd.read_parquet(path= file_path, engine='pyarrow')
        return df
    else:
        print(f"Extracción fallida : no existe el archivo {file_name}")
        return None


def transform(data:pd.DataFrame,categories:list[str]|None,filter_items:Iterable,time_period:list[Date]|None)->pd.DataFrame|None:
    """
    Parametros:
    - data: pandas.DataFrame, Datos de ventas
    - categories: list[str], Lista de columnas por las cuales se quiere filtrar
    - filter_items: typing.Iterable, Objetos por los que se filtrarán los datos
    - time_period: list[Date], Periodo de tiempo por cual se filtrarán los datos

    Regresa:
    - df: pandas.DataFrame, Datos filtrados y transformados
    """
    df = data.copy()
    
    df['year'] = df['date'].dt.year
    df['month'] = df['date'].dt.month
    df['week'] = df['date'].dt.isocalendar().week
    
    categories_in_data = all(elem in df.columns for elem in categories)
    mask= pd.Series(True, index=df.index)

    if time_period is not None:
        period_ts = pd.to_datetime(time_period)
        mask &= df['date'].isin(period_ts)
        
    if (categories is not None) and categories_in_data :
        for c in categories:
            mask &= df[c].isin(filter_items)
    else: 
        print("Transformación fallida: No existen categorías de ordenamiento en los datos")
        return None
    
    return df[mask]


def load(transformed_data:pd.DataFrame,file_path:Path):
    """
    Guarda datos de manera segura en la ruta especificada

    Parametros:
    - transformed_data: pandas.DataFrame, Datos transformados
    - file_path : pathlib.Path, Ruta de escritura
    
    Regresa:
    - ,: None
    """
    save_file_safe(transformed_data,file_path)
    
    print(f"Carga realizada excitosamente en {file_path}")


def main():
    file = "facturas_ventas.parquet"
    print("Iniciando extracción...")
    extracted = extract(file)
    
    branches = list(extracted.branch.unique())
    period = time_period (Date(2020,1,1))
    
    print("Iniciando transformaciones...")


    for b in branches:
        print(b)
        df = transform(
                data=extracted,
                categories=['branch'],
                filter_items=[b],
                time_period=period
            )
        products = list(df.productId.unique())
        for p in products:
            df_filtered = df[df['productId']==p]
            file_path = (
                    data_dir / 'processed' / b / p
                    ).with_suffix('.parquet')
            load(transformed_data=df_filtered, file_path=file_path)
                
    return None


if __name__=='__main__':
    main()