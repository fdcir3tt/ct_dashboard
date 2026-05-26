import pandas as pd

from typing import Any
from common.registry import register
from common.dates import time_period
from airflow.exceptions import AirflowFailException


save_dict = {"historical_existence_documents":"inventory_df"}
tag = "inventory"

def make_storage_dict(branches:pd.DataFrame)->dict[str,list[str]]:
    branches = branches[["storage_id","branch"]]
    branches = branches.set_index("storage_id")["branch"].to_dict()

    branch_storage={}
    for storage_id,branch in branches.items():

        # En caso de haber sucursales con más de un almacen
        if branch in branch_storage.keys():
            branch_storage[branch].append(storage_id)
            continue

        branch_storage[branch]=[storage_id]

    return branch_storage 

@register(tag)
def transform_historical_existence_documents(extracted_data:dict[str,pd.DataFrame|list[dict[str,Any]]],**kwargs)->pd.DataFrame:
        input_data =["historical_existence_documents","branches"]
        for name in input_data:
            if (name not in extracted_data.keys()):
                raise AirflowFailException(f"Task failed,no data to transform:'{name}' ")
        historical_existence_documents = extracted_data["historical_existence_documents"]
        branches                       = extracted_data["branches"]

        # Columnas
        inventory = pd.DataFrame(data=historical_existence_documents)
        inventory["product_id"]= inventory["productoReferencia"].apply( lambda x:x['codigo'])
        inventory =( inventory.drop  (columns=["activo",'productoReferencia'])
                              .rename(columns={"fechaRegistro":"date",
                                               "almacenes":"existence"})
                    )
        if 'costo' in inventory.columns:
            inventory = inventory.drop(columns=['costo'])
        
        inventory["date"] = pd.to_datetime(inventory["date"],errors="coerce", format="mixed")
        inventory["date"] = inventory['date'].dt.date
        inventory['storage_id'] = inventory['existence']
        
        # Transformaciones
        inventory = inventory.explode('storage_id')
        inventory["stock"] = inventory.apply(   lambda r: r["existence"].get(r["storage_id"], 0)
                                                if isinstance(r["existence"], dict)
                                                else 0,
                                                axis=1
                                            )
        inventory.drop(columns='existence',inplace=True)
        
        start_date = str(inventory['date'].min())
        end_date = str(inventory['date'].max())

        
        # Lógica de fechas
        storages = make_storage_dict(branches)
        period = pd.DataFrame(data=time_period(start_date=start_date,end_date=end_date ),
                              columns=["date"])
        period = period.assign(key=1)
        period["date"]=period["date"].dt.date
        storages_inventory = pd.DataFrame({'storage_id': storages})
        storages_inventory['key'] = 1
        period = period.merge(storages_inventory, on='key').drop('key', axis=1)    
        period = period.explode('storage_id')
        
        inventory = period.merge(right=inventory,how='left',on=['date','storage_id'])
        inventory['stock'] = inventory['stock'].fillna(value=0)

    
        print(f"product_id 'nans'{inventory["product_id"].isna().sum()}")
        inventory = inventory.dropna()
        print(f"product_id 'nans'{inventory["product_id"].isna().sum()}")
        
        return inventory


