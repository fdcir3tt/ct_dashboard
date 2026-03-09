import os
import pandas as pd

from pathlib import Path
from typing import Iterable
from mlops.utils import save_file_safe,time_period,data_dir,Date



def extract(file_name:str)->pd.DataFrame|None:
    file_path = data_dir / 'raw' / file_name
    if file_path.exists():
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


def load(transformed_data:pd.DataFrame,
         file_path:Path):
    
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
        categories = list(df.category.unique())
        for c in categories:
            print(f"Categoría:{c}")
            df_filtered = df[df['category']==c]
            if (df_filtered is None) or (df_filtered.empty):
                continue
            products = list(df_filtered.productId.unique())
            
            for p in products:
                
                for w in df_filtered.week.unique():
                    file_path = (
                        data_dir / 'processed' / b / c / p / f'week_{str(w)}'
                        ).with_suffix('.parquet')

                    mask = (df_filtered['week'] == w)
                    load(transformed_data=df_filtered[mask], file_path=file_path)
                
    return None


if __name__=='__main__':
    main()