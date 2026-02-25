import os
import pandas as pd
import json
import datetime
import numpy as np
from pathlib import Path



Date = datetime.datetime
Document =  dict[str, any]
Documents = list[Document]
DATA_PATH = Path('data')


def time_period(start_date: datetime.datetime,end_date: datetime.datetime = datetime.datetime.today()) -> list:
    if start_date > end_date:
        raise ValueError("Fecha inicial debe tomar lugar antes que la fecha final de periodo")

    dates = []
    current = start_date

    while current <= end_date:
        dates.append(current)
        current += datetime.timedelta(days=1)

    return dates


def fill_exchange_rates(rates_dataframe:pd.DataFrame)->pd.DataFrame:
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



def process_exchange_rates(data:pd.DataFrame):
    
    df = data.copy()
    
    # Imputación 
    rates = pd.read_parquet(DATA_PATH/'raw'/'usd_mxn_rates.parquet')
    rates.index = rates.index.date.astype('datetime64[ns]')
    rates.index.name = 'date'
    period = pd.DataFrame(data=time_period(start_date=datetime.datetime(2020,1,1) ),columns=["date"])
    merged = period.merge(df,how="left",on="date")
    merged = merged.merge(rates,how='left',on='date',suffixes=('', '_fill'))
    merged['exchange_rate'] = merged['exchange_rate'].fillna(merged['exchange_rate_fill'])
    merged = merged.drop(columns=['exchange_rate_fill'])

    processed_rates = fill_exchange_rates(rates_dataframe=merged)
    processed_rates = processed_rates.set_index("date") 
    os.makedirs(DATA_PATH/'processed',exist_ok=True)
    processed_rates.to_parquet(DATA_PATH/'processed'/'conversion_usd_mxn_tmp.parquet')
    os.replace(DATA_PATH/'processed'/'conversion_usd_mxn_tmp.parquet',DATA_PATH/'processed'/'conversion_usd_mxn.parquet')

   
def normalize_coins(df:pd.DataFrame)->pd.DataFrame:

    df["price"] = df["price"] * (
        1 - df["sell_coin"] + df["exchange_rate"] * df["sell_coin"]
    )
    df["cost"] = df["cost"] * (
        1 - df["buy_coin"] + df["exchange_rate"] * df["buy_coin"]
    )
    df= df.drop(columns=["sell_coin","buy_coin","exchange_rate"])

    return df


def sales_filters(df:pd.DataFrame)->pd.DataFrame:
    is_sale= (df["quantity"] > 0)&( df["price"] > 0 ) # Solo nos interesan casos donde sí hubo venta
    is_hardware = df["cost"] > 0
    mask = is_sale & is_hardware
    df = df[mask]
    return df

def process_data(invoices:pd.DataFrame,
                 product_codes:pd.DataFrame,
                 exchange_rates:pd.DataFrame,
                 branches:pd.DataFrame,
                 products,
                 categories,
                 update:bool=False):
    """
    Agarra el dataset limpio y listo para procesar para generar las variables 
    útiles/relevantes en el dashboard. 

    """
    file_path = DATA_PATH/'processed'/'facturas_ventas.parquet'
    data_exists= os.path.exists(file_path)
    if (data_exists)&(not update):
        df=pd.read_parquet(file_path)
        return df
    else:
        df = invoices.merge(product_codes,
                            how="inner",on="productId")
        df = df.merge(exchange_rates,
                      how="inner",on="date")
        
        df = normalize_coins(df)
        df = sales_filters(df)

        df['branchId']= df['folio'].str.extract( r'(?P<branchId>[A-Za-z]+)' )
        df = df.merge(branches[["nemonico","sucursal","homoclave"]],
                      how="inner",left_on="branchId",right_on="homoclave")
    
        products = products.merge(categories,
                                  how="left",on="idCategoria")
        products = products [["clave","nombre"]]

        # Columna de estados
        with open("states_dict.json", "r", encoding="utf-8") as f:
            states_dict = json.load(f)

        df["state"] = df["sucursal"].map(states_dict).fillna("UNKNOWN")

        # Categorías
        df = df.merge(products,
                      how="left",left_on="productId",right_on="clave")
        df = df.rename(columns={"nombre":"category"})

        os.makedirs(DATA_PATH/'processed',exist_ok=True)
        df = df.drop_duplicates(subset=['folio','productId','date','clientId'])
        df.to_parquet(DATA_PATH/'processed'/'facturas_ventas_tmp.parquet',index=False)
        os.replace(DATA_PATH/'processed'/'facturas_ventas_tmp.parquet', file_path)
    