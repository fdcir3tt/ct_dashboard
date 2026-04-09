import os
import datetime 
import pandas as pd
import yaml
import numpy as np
import matplotlib.pyplot as plt
import pyodbc

from dotenv import load_dotenv
from pathlib import Path
from typing import Any,Iterable
from dataclasses import dataclass

Date = datetime.date
data_dir = Path('data')

@dataclass
class ExperimentConfig:
    dataset: str
    parameters : dict[str,Any]
    training_data_start_date: Date
    training_data_end_date: Date
    model_type: str
    horizon:int
    frequency: str
    training_window:int
    seed:int
    metrics : list[str]|None=None
    git_commit: str|None =None
    feature_set: str|None =None



@dataclass
class DatasetFilterConfig:
    frequency : str
    horizon: int 
    training_window: int
    start_date: Date|str="oldest"
    end_date: Date|str="latest"
    
    def __post_init__(self):
        if (self.start_date!="oldest") and (self.end_date!="latest") :
            if self.start_date > self.end_date:
                raise ValueError("'start_date' debe ser una fecha antes de 'end_date'")

        if self.horizon <= 0:
            raise ValueError("'horizon' debe ser positivo")

        if self.training_window <= 0:
            raise ValueError("'training_window' must be positive")

        if self.frequency not in {"daily", "weekly", "monthly"}:
            raise ValueError("'frequency' debe ser uno de los siguientes valores: daily, weekly, monthly")
    

class DatasetFilters:
    def __init__(self, config: DatasetFilterConfig):
        self.cfg = config

    def apply_period_filter(self, data: pd.DataFrame)->pd.DataFrame:
        """
        Aplica filtro de periodo especificado a los datos
        
        Parametros:
        - data: pandas.DataFrame, Datos que se quieren filtrar

        Regresa:
        - df: pandas.DataFrame, Datos filtrados
        """
        
        if self.cfg.start_date=="oldest":
            start_date = pd.to_datetime( data['date'].min())
        else:
            start_date = pd.to_datetime(self.cfg.start_date)
        

        if self.cfg.end_date=="latest":
            end_date = pd.to_datetime( data['date'].max() )
        else:    
            end_date = pd.to_datetime(self.cfg.end_date)
        
        mask = (
            (data['date'] >= start_date) &
            (data['date'] <= end_date) 
        )
        
        df = data[mask]
        
        if df.empty:
            print("Dataset invalido: No hay datos en el periodo específicado")
            return pd.DataFrame()
        df = df.sort_values("date")
        return df
    
    def prepare_series(self,data:pd.DataFrame)->tuple[np.ndarray[Date],np.ndarray[int]]:
        """
        Agarra un dataset de pandas y lo convierte en un par de series, uno de los valores
        del periodo y otro con las fechas del periodo. 

        Parametros: 
        - data:pandas.DataFrame, Datos que se quieren convertir a serie de tiempo  

        Regresa:
        - x: numpy.ndarray, Serie que contiene fechas del periodo
        - y: numpy.ndarray, Series que contiene los valores del periodo
        """
        df = self.apply_period_filter(data)
        
        
        # Frecuencia
        if self.cfg.frequency == "daily":
            target_column = "quantity"
        
        if self.cfg.frequency == "weekly":
            df["weekly_quantity"]=df.groupby(["year","week"])["quantity"].transform("sum")
            target_column="weekly_quantity"

        if self.cfg.frequency == "monthly": 
            df["monthly_quantity"]=df.groupby(["year","month"])["quantity"].transform("sum")
            target_column="monthly_quantity"
        
        
        
        if self.cfg.start_date=="oldest":
            start_date = pd.to_datetime( data['date'].min())
        else:
            start_date = pd.to_datetime(self.cfg.start_date)
        

        if self.cfg.end_date=="latest":
            end_date = pd.to_datetime( data['date'].max() )
        else:    
            end_date = pd.to_datetime(self.cfg.end_date)

        period = time_period(start_date=start_date,end_date=end_date)
        if df.empty:
            x,y = make_time_series(pd.DataFrame(data=[[start_date,0]],columns=["date","quantity"]),period,target_column)
        else:
            x,y = make_time_series(df,period,target_column)
        return x,y
    
    def apply_split(self, data: pd.DataFrame)->tuple[np.ndarray[Date],np.ndarray[int],np.ndarray[Date],np.ndarray[int]]|None:
        """
        Divide datos en datos de entrenamiento y de prueba en base los parametros
        de frecuencia, ventana de entrenamiento y ventana de horizonte.

        Parametros:
        - data: pandas.DataFrame, Datos filtrados que se quieren dividir

        Regresa:
        - x_train: numpy.ndarray, Datos de entrada de entrenamiento
        - y_train: numpy.ndarray, Datos de objetivo de entrenamiento
        - x_test: numpy.ndarray, Datos de entrada de prueba
        - y_test: numpy.ndarray, Datos de objetivo de prueba
        """

        x,y = self.prepare_series(data)

        # Ventanas de entrenamiento y horizonte
        training_window = self.cfg.training_window
        horizon = self.cfg.horizon

        if len(y)< horizon+training_window:
            print(f"Dataset invalido: Insuficiente datos para configuración actual.\nNúmero de datos:{len(y)}\nNúmero Requerido:{horizon+training_window}")
            return None
        
        x_train = x[:training_window]
        y_train = y[:training_window]

        x_test = x[training_window:training_window+horizon]
        y_test = y[training_window:training_window+horizon]

        return x_train,y_train,x_test,y_test

def time_period(start_date: Date,end_date: Date = Date.today()) -> list[Date]:
    """
    Genera una lista de fechas en el periodo designado

    Parametros:
    - start_date: Date , Fecha inicio del periodo
    - end_date: Date , Fecha fin del periodo
    
    Regresa:
    - dates:list[Date], Lista de fechas entre 'start_date' y 'end_date'
    """
    if start_date > end_date:
        raise ValueError("Fecha inicial debe tomar lugar antes que la fecha final de periodo")

    dates = []
    current = start_date

    while current <= end_date:
        dates.append(current)
        current += datetime.timedelta(days=1)

    return dates

def save_file_safe(data: pd.DataFrame, file_path: Path) -> None:
    """
    Recibe un dataframe de pandas y la guarda de manera segura en ubicación específicada
    
    Parametros:
    - data: pandas.DataFrame , Datos que se quieren almacenar
    - file_path: pathlib.Path , Ubicación en donde se quieren almacenar los datos

    Regresa:
    -, :None
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)

    tmp_path = file_path.with_suffix(file_path.suffix + ".tmp")
    data.to_parquet(tmp_path, engine='pyarrow',index=False)

    os.replace(tmp_path, file_path)

def get_experiment_config(file_path:Path=Path('params.yaml'))->ExperimentConfig:
    """
    Lee archivo de configuración de experimentos y lo carga como objeto de configuración

    Parametros:
    - file_path: pathlib.Path , Ubicación de archivo de configuración. 
    
    Regresa:
    - ExperimentConfig(**config): ExperimentConfig, Configuración de experimento
    """
    if file_path.suffix=='.yml' or file_path.suffix=='.yaml':
        with open(file_path, mode='r') as f:
            config = yaml.safe_load(f)
        config["training_data_start_date"] = Date.fromisoformat(config["training_data_start_date"])
        config["training_data_end_date"]  = Date.fromisoformat(config["training_data_end_date"])
    return ExperimentConfig(**config)

def get_client_list()->pd.DataFrame:
    """
    Extrae claves de clientes registrados en el Data Ware House. 

    Parametros:
    - :None,
    Regresa:
    - df: pandas.Dataframe, Columna que contiene las claves de cliente
    """
    load_dotenv()
    
    connection_str = (
        f'DRIVER={{{os.getenv("DATA_WAREHOUSE_DRIVER")}}};'
        f'SERVER={os.getenv ("DATA_WAREHOUSE_IP") };'  
        f'DATABASE={os.getenv("DATA_WAREHOUSE_DB_NAME")};'  
        f'UID={os.getenv("DATA_WAREHOUSE_USER_ID")};'  
        f'PWD={os.getenv("DATA_WAREHOUSE_USER_PWD")}'   
    )
    query = f""" SELECT {os.getenv("ID_COLUMN")} FROM {os.getenv("CLIENTS_TABLE_NAME")}"""

    try:
        
        conn = pyodbc.connect(connection_str)
        print("Conexión exitosa a la base de datos!")
        
        df = pd.read_sql(query,conn)
        conn.close()
        df = df.rename(columns={os.getenv("ID_COLUMN"):"clientId"})

        return df

    except pyodbc.Error as e:
        print(f"Error al intentar conectarse a la base de datos: {e}")
    

def make_time_series(data:pd.DataFrame,period:list[Date]|None=None,target_column:str="quantity",frequency:str="daily")-> np.ndarray:
    """
    Convierte datos de ventas a serie temporal, llenando los huecos de fechas con venta '0'

    Parametros:
    - data: pandas.DataFrame, Datos de venta
    - period: list[Date], Periodo de tiempo de interes
    - target_column: str, Columna objetivo de serie
    - frequency: str, Frecuencia de serie. Ej. 'days','weeks','months' 
    Regresa:
    - time_series: numpy.ndarray, Serie de tiempo resultado de los datos de venta
    - time_axis: numpy.ndarray, Fechas de serie de tiempo
    """
    df = data.copy()
    if period is None:
        period = time_period(start_date=Date(2020,1,1))
    time_df = pd.DataFrame(data=period,columns=["date"])
    time_df["date"]=pd.to_datetime(time_df["date"])

    if "year" not in time_df.columns:
        df["year"] = df["date"].dt.year

    if frequency=="daily":
        frequency_col = "day"
        df["day"]=df["date"].dt.dayofyear

    if frequency=="weekly":
        frequency_col = "week"

    if frequency=="monthly":
        frequency_col = "month"

    df["quantity"]= df.groupby(["year",frequency_col])["quantity"].transform("sum")
    df = df.drop_duplicates(subset=["year",frequency_col,"quantity"])

    df = time_df.merge(right=df,
                       how="left",
                       on="date")
    
    df[target_column]=df[target_column].fillna(value=0,inplace=False)
    df = df.sort_values(by="date")

    

    time_axis = df["date"].to_numpy()
    time_series= df[target_column].to_numpy()
    return time_axis,time_series


def plot_series(series:np.ndarray,title:str="Ventas realizadas dentro del periodo",xlabel:str="Tiempo (días)", ylabel:str="Ventas"):
    """
    Gráfica de predicción de modelo y datos reales.
            
    Parametros:
    - series: array-like, Valores de venta
    - title: str, Título de gráfico
    - xlabel: str, Etiqueta de eje horizontal
    - ylabel: str,  Etiqueta de eje vertical

    Regresa:
    - fig: matplotlib Figure object, Gráfica de ventas 
    """
    fig, ax = plt.subplots(figsize=(10,5))
    ax.plot(series, label="Ventas", marker='x')
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.legend()
    ax.grid(True)
    return fig

def load_dataset(dataset:str,config:ExperimentConfig|dict[str,Any],train_split:bool=True)->tuple|pd.DataFrame:
    """
    Carga datos que se utilizaran para el experimento de entrenamiento de un modelo

    Parametros:
    - model_name: str, Nombre del tipo de modelo siendo utilizado
    - dataset: str, Nombre de los datos que se quieren utilizar
    - config: ExperimentConfig, Configuración del experimento

    Regresa:
    - df: pandas.DataFrame, Datos con filtro de periodo
    - x_train: numpy.ndarray, Datos de entrada de entrenamiento
    - y_train: numpy.ndarray, Datos de objetivo de entrenamiento
    - x_test: numpy.ndarray, Datos de entrada de prueba
    - y_test: numpy.ndarray, Datos de objetivo de prueba
    """
    branch, productId = dataset.split('_', 1)
    file_path = data_dir/'processed'/ branch / f'{productId}.parquet'
    
    data = pd.read_parquet(file_path)
    if isinstance(config,ExperimentConfig):
        dataset_config = DatasetFilterConfig(start_date= config.training_data_start_date,
                                            end_date= config.training_data_end_date,
                                            frequency= config.frequency,
                                            horizon= config.horizon,
                                            training_window=config.training_window)
    else:
        dataset_config = DatasetFilterConfig(start_date=config["training_data_start_date"],
                                             end_date=config["training_data_end_date"],
                                             frequency=config["frequency"],
                                             horizon= config["horizon"],
                                             training_window= config["training_window"])
        
    df = DatasetFilters(dataset_config).apply_period_filter(data)
    
    if train_split:
        x_train,y_train,x_test,y_test = DatasetFilters(dataset_config).apply_split(data)
        return df,x_train,y_train,x_test,y_test
    
    return df



