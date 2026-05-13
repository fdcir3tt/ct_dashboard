import hashlib
import pandas as pd

from typing import Any
from common.data import save_data,load_data
from common.dates import time_period

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

def transform(historical_existence_documents:dict[str,Any],branches:pd.DataFrame)->pd.DataFrame:
        inventory = pd.DataFrame(data=historical_existence_documents)
        inventory["product_id"]= inventory["productoReferencia"].apply( lambda x:x['codigo'])
        inventory =( inventory.drop(columns=["activo",'productoReferencia','costo'])
                .rename(columns={"fechaRegistro":"date",
                                 "almacenes":"existence"}))
        inventory["date"] = pd.to_datetime(inventory["date"])
        inventory["date"] = inventory['date'].dt.date
        inventory['storage_id'] = inventory['existence']
        inventory = inventory.explode('storage_id')
        inventory["stock"] = inventory.apply(
                                                lambda r: r["existence"].get(r["storage_id"], 0)
                                                if isinstance(r["existence"], dict)
                                                else 0,
                                                axis=1
                                            )
        inventory.drop(columns='existence',inplace=True)
        
        start_date = str(inventory['date'].min())
        end_date = str(inventory['date'].max())

        
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
        inventory["existence_id"] = (
                                    inventory["product_id"].astype(str)
                                    + "-" + inventory["storage_id"].astype(str)
                                    + "-" + inventory["date"].astype(str)
                                ).map(lambda x: hashlib.md5(x.encode()).hexdigest())
        return inventory

def run_transform(**context):
    path_strings = context["ti"].xcom_pull(task_ids="extract_historical_data_and_branches", key="path_strings")
    extracted_data = load_data(path_strings)
    
    historical_existence_documents = extracted_data["historical_existence_documents"]
    branches = extracted_data["branches"]

    transformed_data = transform(historical_existence_documents,branches)
 
    inventory_path ="/tmp/inventory.parquet"
    save_data(transformed_data,inventory_path)

    context["ti"].xcom_push(key="inventory_path", value=inventory_path)
    