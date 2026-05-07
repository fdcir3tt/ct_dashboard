import hashlib
import pandas as pd

from typing import Any
from pathlib import Path
from common.paths import load_records,delete_files
from common.dates import time_period

def make_storage_dict(branches:pd.DataFrame)->dict[str,list[str]]:
    
    branches = branches[["storageId","branch"]]
    branches = branches.set_index("storageId")["branch"].to_dict()

    branch_storage={}
    for storageId,branch in branches.items():

        # En caso de haber sucursales con más de un almacen
        if branch in branch_storage.keys():
            branch_storage[branch].append(storageId)
            continue

        branch_storage[branch]=[storageId]

    return branch_storage 

def transform(historical_existence_documents:dict[str,Any],branches:pd.DataFrame)->pd.DataFrame:
        inventory = pd.DataFrame(data=historical_existence_documents)
        inventory["productId"]= inventory["productoReferencia"].apply( lambda x:x['codigo'])
        inventory =( inventory.drop(columns=["activo",'productoReferencia','costo'])
                .rename(columns={"fechaRegistro":"date",
                                 "almacenes":"existence"}))
        inventory["date"] = pd.to_datetime(inventory["date"])
        inventory["date"] = inventory['date'].dt.date
        inventory['storageId'] = inventory['existence']
        inventory = inventory.explode('storageId')
        inventory["stock"] = inventory.apply(
                                                lambda r: r["existence"].get(r["storageId"], 0)
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
        storages_inventory = pd.DataFrame({'storageId': storages})
        storages_inventory['key'] = 1
        period = period.merge(storages_inventory, on='key').drop('key', axis=1)    
        period = period.explode('storageId')
        
        inventory = period.merge(right=inventory,how='left',on=['date','storageId'])
        inventory['stock'] = inventory['stock'].fillna(value=0)

    
        print(f"productId 'nans'{inventory["productId"].isna().sum()}")
        inventory = inventory.dropna()
        print(f"productId 'nans'{inventory["productId"].isna().sum()}")
        inventory["existenceId"] = (
                                    inventory["productId"].astype(str)
                                    + "-" + inventory["storageId"].astype(str)
                                    + "-" + inventory["date"].astype(str)
                                ).map(lambda x: hashlib.md5(x.encode()).hexdigest())
        return inventory

def run_transform(**context):
    historical_path = Path(context["ti"].xcom_pull(task_ids="extract_historical_data_and_branches", key="historical_existence_documents_path"))
    historical_existence_documents = load_records(historical_path)

    branches_path = Path(context["ti"].xcom_pull(task_ids="extract_historical_data_and_branches", key="branches_path" ))
    branches = pd.read_parquet(branches_path,engine="pyarrow")

    transformed_data = transform(historical_existence_documents,branches)
    delete_files([historical_path,branches_path])

    inventory = transformed_data
    inventory_path =Path("/tmp/inventory.parquet")
    inventory.to_parquet(inventory_path,engine="pyarrow")

    context["ti"].xcom_push(key="inventory_path", value=str(inventory_path))