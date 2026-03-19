import pandas as pd
import os
from mlops.utils import data_dir,Date,save_file_safe




def get_dataset(branch:str,productId:str,time_period:list[Date]|None=None)->pd.Dataframe:
    """
    Extrae dataset 
    """
    file_path = (data_dir/ 'processed' / branch / productId).with_suffix('.parquet')
    dataset = pd.read_parquet(file_path)

    if time_period:
        mask = dataset['date'].isin(time_period)
        return dataset [mask]
    
    return dataset


def dataset_profiling(branch:str,productId:str,time_period:list[Date],description:str)->None:
    """
    Función que guarda metadatos de un dataset en tabla correspondiente
    """
    
    def make_dataset_id(branch:str)->str:
        id_file_path = data_dir / 'raw' / 'dataset_ids.parquet'
        if os.path.isfile(id_file_path):
            dataset_ids = pd.read_parquet(id_file_path)
            dataset_ids['id_integer'] = dataset_ids['id'].apply(lambda x: int( x.split('_')[2] ) )
            x = dataset_ids['id_integer'].max()
            x += 1
        else :
            x = 1

        return f'{branch}_{productId}_{str(x)}'
    
    
    new_row =pd.DataFrame( {'id': make_dataset_id(branch) ,
                            'time_period':(time_period[0],time_period[-1]), 
                            'description':description})

    id_file_path = data_dir / 'raw' / 'dataset_ids.parquet'
    if os.path.isfile(id_file_path):
        dataset_ids = pd.read_parquet(id_file_path)
        save_file_safe(data=dataset_ids.concat([dataset_ids,new_row],ignore_index=True),
                       file_path =id_file_path)
    else:
        save_file_safe(data=new_row,file_path=id_file_path)