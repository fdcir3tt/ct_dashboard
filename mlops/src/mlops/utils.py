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
from dataclasses import dataclass,replace

DEBUG = False
Date = datetime.date
data_dir = Path('data')

@dataclass
class Metrics:
    """
    Contenedor de métricas de evaluación para modelos de pronóstico.

    Parameters
    ----------
    mae : float | None, default=None
        Error absoluto medio (*Mean Absolute Error*).
    mfe : float | None, default=None
        Error medio de pronóstico (*Mean Forecast Error*).
    rmse : float | None, default=None
        Raíz del error cuadrático medio (*Root Mean Squared Error*).
    da : float | None, default=None
        Precisión direccional (*Directional Accuracy*).

    Raises
    ------
    ValueError
        Si `rmse`, `mae` o `da` son menores o iguales a cero.

    Notes
    -----
    Todas las métricas son opcionales y se validan únicamente cuando
    contienen un valor distinto de ``None``.
    """
    mae: float |None = None
    mfe : float|None = None
    rmse : float |None = None
    da:float|None = None

    def __post_init__(self):
        if self.rmse:
            if self.rmse <= 0:
                raise ValueError("Raíz del error cuadrado promedio debe ser positivo")
        if self.mae:  
            if self.mae <= 0:
                raise ValueError("Error absoluto promedio debe ser positivo")
            
        if self.da:
            if self.da <= 0:
                raise ValueError("Error direccional debe ser positivo")
            
@dataclass
class ExperimentConfig:
    """
    Configuración general para experimentos de entrenamiento y evaluación.

    Parameters
    ----------
    dataset : str
        Nombre del conjunto de datos utilizado.
    parameters : dict[str, Any]
        Diccionario con hiperparámetros del modelo.
    model_type : str
        Tipo de modelo utilizado en el experimento.
    horizon : int
        Número de periodos a predecir.
    frequency : str
        Frecuencia temporal de los datos. Valores válidos:
        ``"daily"``, ``"weekly"`` o ``"monthly"``.
    training_window : int
        Número de observaciones utilizadas para entrenamiento.
    seed : int
        Semilla para reproducibilidad.
    training_data_start_date : Date | str, default="oldest"
        Fecha inicial de entrenamiento.
    training_data_end_date : Date | str, default="latest"
        Fecha final de entrenamiento.
    metrics : list[str] | None, default=None
        Lista de métricas a calcular.
    git_commit : str | None, default=None
        Hash del commit asociado al experimento.
    feature_set : str | None, default=None
        Nombre del conjunto de características utilizado.

    Methods
    -------
    copy()
        Retorna una copia superficial de la configuración.
    """
    dataset: str
    parameters : dict[str,Any]
    model_type: str
    horizon:int
    frequency: str
    training_window:int
    seed:int
    training_data_start_date: Date|str="oldest"
    training_data_end_date: Date|str="latest"
    metrics : list[str]|None=None
    git_commit: str|None =None
    feature_set: str|None =None

    def copy(self):
        """
        Genera una copia de la configuración actual.

        Returns
        -------
        ExperimentConfig
            Nueva instancia con los mismos atributos.
        """
        return replace(self)

@dataclass
class DatasetFilterConfig:
    """
    Configuración para filtrado y segmentación de series temporales.

    Parameters
    ----------
    frequency : str
        Frecuencia temporal de la serie. Valores válidos:
        ``"daily"``, ``"weekly"`` o ``"monthly"``.
    horizon : int
        Número de observaciones utilizadas para prueba.
    training_window : int
        Número de observaciones utilizadas para entrenamiento.
    start_date : Date | str, default="oldest"
        Fecha inicial del periodo.
    end_date : Date | str, default="latest"
        Fecha final del periodo.

    Raises
    ------
    ValueError
        Si las fechas son inválidas, si `horizon` o
        `training_window` son menores o iguales a cero,
        o si `frequency` no es válida.
    """
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
    """
    Utilidades para filtrar, transformar y dividir series temporales.

    Parameters
    ----------
    config : DatasetFilterConfig
        Configuración de filtros y segmentación.

    Attributes
    ----------
    cfg : DatasetFilterConfig
        Configuración asociada a la instancia.
    """
    def __init__(self, config: DatasetFilterConfig):
        self.cfg = config

    def apply_period_filter(self, data: pd.DataFrame)->pd.DataFrame:
        """
        Filtra un conjunto de datos según el rango de fechas configurado.

        Parameters
        ----------
        data : pandas.DataFrame
            Datos de entrada. Debe contener una columna ``date``.

        Returns
        -------
        pandas.DataFrame
            Datos filtrados y ordenados cronológicamente.

        Notes
        -----
        Si el filtro produce un conjunto vacío, se genera un
        DataFrame auxiliar con valores de cantidad igual a cero.
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
            if DEBUG:
                print("Dataset vacío: No hay datos en el periodo específicado")
            if not data.empty:
                productId = data["productId"].iloc[0]
            df = pd.DataFrame(data=[{"quantity":0,"date":start_date,"productId":productId,"clientId":"NO_CLIENT"},{"quantity":0,"date":end_date,"productId":productId,"clientId":"NO_CLIENT"}])
            df ["month"] = df["date"].dt.month
            df ["year"] = df["date"].dt.year
            return df
        df = df.sort_values("date")
        return df
    
    def prepare_series(self,data:pd.DataFrame)->tuple[np.ndarray[Date],np.ndarray[int]]:
        """
        Convierte un conjunto de datos en una serie temporal.

        Parameters
        ----------
        data : pandas.DataFrame
            Datos de entrada con información temporal y cantidades.

        Returns
        -------
        tuple[numpy.ndarray, numpy.ndarray]
            Tupla con:

            - ``x``: arreglo de fechas.
            - ``y``: arreglo de valores agregados.

        Notes
        -----
        La agregación depende de la frecuencia configurada:

        - ``daily``: valores diarios.
        - ``weekly``: suma semanal.
        - ``monthly``: suma mensual.
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
        Divide una serie temporal en entrenamiento y prueba.

        Parameters
        ----------
        data : pandas.DataFrame
            Datos de entrada.

        Returns
        -------
        tuple[numpy.ndarray, numpy.ndarray, numpy.ndarray, numpy.ndarray] | None
            Tupla con:

            - ``x_train``: fechas de entrenamiento.
            - ``y_train``: valores de entrenamiento.
            - ``x_test``: fechas de prueba.
            - ``y_test``: valores de prueba.

            Retorna ``None`` si no existen suficientes datos.

        Notes
        -----
        El tamaño de entrenamiento y prueba se determina mediante
        ``training_window`` y ``horizon``.
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
    Genera una lista de fechas consecutivas entre dos fechas.

    Parameters
    ----------
    start_date : Date
        Fecha inicial del periodo.
    end_date : Date, default=Date.today()
        Fecha final del periodo.

    Returns
    -------
    list[Date]
        Lista de fechas entre ``start_date`` y ``end_date``.

    Raises
    ------
    ValueError
        Si ``start_date`` es posterior a ``end_date``.
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
    Guarda un DataFrame en formato parquet de manera segura.

    Parameters
    ----------
    data : pandas.DataFrame
        Datos a almacenar.
    file_path : pathlib.Path
        Ruta destino del archivo.

    Returns
    -------
    None

    Notes
    -----
    El archivo se guarda primero en una ruta temporal y luego
    se reemplaza el archivo final para evitar corrupción.
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)

    tmp_path = file_path.with_suffix(file_path.suffix + ".tmp")
    data.to_parquet(tmp_path, engine='pyarrow',index=False)

    os.replace(tmp_path, file_path)

def get_experiment_config(file_path:Path=Path('params.yaml'))->ExperimentConfig:
    """
    Carga la configuración de un experimento desde un archivo YAML.

    Parameters
    ----------
    file_path : pathlib.Path, default=Path("params.yaml")
        Ruta del archivo de configuración.

    Returns
    -------
    ExperimentConfig
        Configuración cargada del experimento.

    Notes
    -----
    Las fechas se convierten automáticamente desde formato ISO.
    """
    if file_path.suffix=='.yml' or file_path.suffix=='.yaml':
        with open(file_path, mode='r') as f:
            config = yaml.safe_load(f)
        config["training_data_start_date"] = Date.fromisoformat(config["training_data_start_date"])
        config["training_data_end_date"]  = Date.fromisoformat(config["training_data_end_date"])
    return ExperimentConfig(**config)

def get_client_list()->pd.DataFrame:
    """
    Obtiene la lista de clientes registrados.

    Returns
    -------
    pandas.DataFrame
        DataFrame con identificadores de clientes.

    Notes
    -----
    Si existe un archivo local previamente almacenado,
    se utiliza en lugar de consultar el Data Warehouse.
    """
    file =data_dir/'raw'/'clients.parquet'
    if file.exists():
        local_df = pd.read_parquet(file)
        return local_df
    
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
        save_file_safe(df,file)

        return df

    except pyodbc.Error as e:
        print(f"Error al intentar conectarse a la base de datos: {e}")
    

def make_time_series(data:pd.DataFrame,period:list[Date]|None=None,target_column:str="quantity",frequency:str="daily")-> np.ndarray:
    """
    Convierte datos tabulares en una serie temporal continua.

    Parameters
    ----------
    data : pandas.DataFrame
        Datos de ventas.
    period : list[Date] | None, default=None
        Periodo temporal objetivo.
    target_column : str, default="quantity"
        Nombre de la columna objetivo.
    frequency : str, default="daily"
        Frecuencia temporal de agregación.

    Returns
    -------
    tuple[numpy.ndarray, numpy.ndarray]
        Tupla con:

        - ``time_axis``: arreglo de fechas.
        - ``time_series``: arreglo de valores.

    Notes
    -----
    Las fechas faltantes se rellenan con valores iguales a cero.
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
    Genera una gráfica de una serie temporal.

    Parameters
    ----------
    series : numpy.ndarray
        Valores de la serie temporal.
    title : str, default="Ventas realizadas dentro del periodo"
        Título de la gráfica.
    xlabel : str, default="Tiempo (días)"
        Etiqueta del eje X.
    ylabel : str, default="Ventas"
        Etiqueta del eje Y.

    Returns
    -------
    matplotlib.figure.Figure
        Figura generada.
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
    Carga y filtra un conjunto de datos para entrenamiento.

    Parameters
    ----------
    dataset : str
        Nombre del dataset.
    config : ExperimentConfig | dict[str, Any]
        Configuración del experimento.
    train_split : bool, default=True
        Indica si se debe dividir en entrenamiento y prueba.

    Returns
    -------
    tuple | pandas.DataFrame
        Si ``train_split=True`` retorna:

        - ``df``
        - ``x_train``
        - ``y_train``
        - ``x_test``
        - ``y_test``

        En caso contrario, retorna únicamente el DataFrame filtrado.
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



def calculate_metrics(y_pred:np.ndarray,y_true:np.ndarray,test_metrics:list[str]=['mae','mfe','rmse','da'])->Metrics:
    """
        Calcula métricas de evaluación para predicciones.

        Parameters
        ----------
        y_pred : numpy.ndarray
            Valores predichos por el modelo.
        y_true : numpy.ndarray
            Valores reales observados.
        test_metrics : list[str], default=["mae", "mfe", "rmse", "da"]
            Métricas a calcular.

        Returns
        -------
        Metrics
            Objeto con las métricas calculadas.

        Notes
        -----
        Métricas soportadas:

        - ``mae``: error absoluto medio.
        - ``mfe``: error medio de pronóstico.
        - ``rmse``: raíz del error cuadrático medio.
        - ``da``: precisión direccional.
    """
    def directional_accuracy(y_pred:np.ndarray,y_true:np.ndarray)->float:
        true_direction =np.sign(y_true[1:] - y_true[:-1])
        pred_direction =np.sign(y_pred[1:] - y_pred[:-1])
        d_i = (true_direction == pred_direction).astype(float)
        return d_i.mean()
        
    if len(y_pred)!=len(y_true):
        print(f"Discrepancia en cantidad de datos :  y_pred = {len(y_pred)} , y_true = {len(y_true)}")
        return Metrics()
    result_metrics = {} 
    for m in test_metrics:
        if m=='mae': # Mean Absolute Error
            result_metrics['mae'] = np.mean(abs(y_true-y_pred))

        if m=='mfe':# Mean Forecast Error
            result_metrics['mfe'] = np.mean(y_pred-y_true)
                
        if m=='rmse':# Root Mean Square Error
            result_metrics['rmse'] = np.sqrt( np.mean( (y_true-y_pred)**2 ) )

        if m=='da':# Directional Accuracy
            result_metrics['da'] = directional_accuracy(y_pred,y_true)
    return Metrics(**result_metrics)

def calculate_iqr_bounds(sales_series:pd.Series)->tuple[float,float]:
    """
    Calcula límites basados en rango intercuartílico (IQR).

    Parameters
    ----------
    sales_series : pandas.Series
        Serie numérica de ventas.

    Returns
    -------
    tuple[float, float]
        Límite inferior y superior para detección de outliers.

    Notes
    -----
    Los límites se calculan usando:

    ``Q1 - 1.5 * IQR`` y ``Q3 + 1.5 * IQR``.
    """
    q1 = sales_series.quantile(0.25)
    q3 = sales_series.quantile(0.75)
    iqr = q3 - q1
    return (q1 - 1.5 * iqr, q3 + 1.5 * iqr)


def identify_outlier_sales(data: pd.DataFrame,
                           element_column:str)->pd.DataFrame:
    """
    Identifica registros atípicos en datos de ventas.

    Parameters
    ----------
    data : pandas.DataFrame
        Datos de ventas.
    element_column : str
        Columna utilizada para agrupar elementos.

    Returns
    -------
    pandas.DataFrame
        DataFrame con una columna booleana ``is_outlier``.

    Notes
    -----
    Los outliers se identifican utilizando límites basados
    en rango intercuartílico (IQR).
    """
    df = data.copy()

    bounds_dict = df.groupby(element_column)['quantity'].apply(calculate_iqr_bounds).to_dict()
    
    df['iqr_bounds'] = df[element_column].map(bounds_dict)
    df['is_outlier'] = ~df['quantity'].between(
                                              df['iqr_bounds'].str[0], 
                                              df['iqr_bounds'].str[1]
                                              )

    df = df.drop(columns='iqr_bounds')
    return df