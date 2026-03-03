import os
import pandas as pd

from pathlib import Path
from typing import Iterable
from mlops.utils import save_file_safe,time_period,data_dir,Date



def extract(file_name:str)->pd.DataFrame|None:
    file_path = data_dir / 'raw' / file_name
    if os.path.exists(file_path):
        return pd.read_parquet(path= file_path, engine='pyarrow')
    else:
        print(f"Extracción fallida : no existe el archivo {file_name}")
        return None


def transform(data:pd.DataFrame,
              categories:list[str]|None,filter_items:Iterable,
              time_period:list[Date]|None)->pd.DataFrame|None:

    df = data.copy()
    
    df['year'] = df['date'].dt.year
    df['month'] = df['date'].dt.month
    df['week'] = df['date'].dt.isocalendar().week

    mask = True
    if time_period is not None:
        mask &= df['date'].isin(values=time_period)

    if (categories is not None) and all(elem in categories for elem in df.columns):
        for c in categories:
            mask &= df[c].isin(values=filter_items)
    else: 
        print("Transformación fallida: No existen categorías de ordenamiento en los datos")
        return None
    
    return df[mask]


def load(transformed_data:pd.DataFrame,
         file_path:Path):
    save_file_safe(transformed_data,file_path)
    print("Carga realizada excitosamente")


def main():
    file = "facturas_ventas.parquet"
    extracted = extract(file)
    
    branches = list[extracted.branch.unique()]
    categories = list[extracted.category.unique()]
    
    period = time_period (Date(2020,1,1))
    
    
    for b in branches:
        for c in categories:
            df = transform(data=extracted,
                           categories=['branch','category'],
                           filter_items=[b,c],
                           time_period=period)
            products = list[df.productId.unique()]
            for p in products:
                for m in df.month.unique():
                    for w in df.week.unique():
                        file_path = data_dir / 'processed' / b / c / p / m / w + '.parquet' 
                        mask = (df['month']==m) & (df['week']==w)
                        load(transformed_data=df[mask],file_path=file_path)
                        
        
        
            



    return None


if __name__=='main':
    main()