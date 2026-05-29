import pandas as pd
import os
from mlops.utils import data_dir,Date,save_file_safe




def get_dataset(branch:str,productId:str,time_period:list[Date]|None=None)->pd.Dataframe:
    """
    Carga el dataset procesado de un producto y sucursal desde archivo Parquet.

    Construye la ruta del archivo a partir de `branch` y `productId` dentro
    del directorio `data/processed/`. Opcionalmente filtra los datos para
    incluir solo las fechas contenidas en `time_period`.

    Parameters
    ----------
    branch : str
        Nombre de la sucursal. Corresponde al subdirectorio dentro de
        `data/processed/`.
    productId : str
        Identificador del producto. Corresponde al nombre del archivo
        Parquet (sin extensión).
    time_period : list of Date, optional
        Lista de fechas a incluir en el resultado. Si es None, se retorna
        el dataset completo sin filtrar. Por defecto None.

    Returns
    -------
    pd.DataFrame
        DataFrame con los datos del producto en la sucursal indicada,
        filtrado por las fechas de `time_period` si se proporcionan.
    """
    file_path = (data_dir/ 'processed' / branch / productId).with_suffix('.parquet')
    dataset = pd.read_parquet(file_path)

    if time_period:
        mask = dataset['date'].isin(time_period)
        return dataset [mask]
    
    return dataset


def dataset_profiling(branch:str,productId:str,time_period:list[Date],description:str)->None:
    """
    Registra los metadatos de un dataset en la tabla de perfilado central.

    Genera un identificador único para el dataset y almacena su período
    de cobertura y descripción en el archivo `data/raw/dataset_ids.parquet`.
    Si el archivo no existe, lo crea; si ya existe, agrega el nuevo registro.

    Parameters
    ----------
    branch : str
        Nombre de la sucursal asociada al dataset. Se usa como prefijo
        en la generación del identificador único.
    productId : str
        Identificador del producto asociado al dataset. Se usa como segundo
        componente en el identificador único.
    time_period : list of Date
        Lista de fechas que cubre el dataset. Se almacena como tupla
        ``(time_period[0], time_period[-1])`` representando inicio y fin.
    description : str
        Texto descriptivo sobre el contenido o propósito del dataset.

    Returns
    -------
    None

    Notes
    -----
    El identificador único sigue el formato ``'{branch}_{productId}_{n}'``,
    donde ``n`` es el entero siguiente al máximo ID registrado en la tabla.
    Si no existe tabla previa, ``n`` comienza en 1.

    La función auxiliar interna `make_dataset_id` es responsable de
    calcular y construir dicho identificador.
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