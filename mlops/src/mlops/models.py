import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from mlops.utils import get_client_list,ExperimentConfig,DatasetFilterConfig,DatasetFilters
from typing import Iterable,Any
from matplotlib.figure import Figure
from dataclasses import dataclass
from abc import ABC,abstractmethod


@dataclass
class Metrics:
    mae: float |None = None
    mfe : float|None = None
    mse : float |None = None
    da:float|None = None

@dataclass
class LossHistory:
    train_loss:Iterable|None=None
    test_loss:Iterable|None=None
        
class ForecastModel(ABC):
    _registry: dict[str, type["ForecastModel"]] = {}

    def __init__(self,parameters:dict[str,Any],test_metrics:list[str]=['mae','mse']):
        self.parameters= parameters
        self.test_metrics = test_metrics # Metricas que se quieren evaluar


    @classmethod
    def register(cls, name: str):
        """ Decorador para registrar modelos de esta clase automáticamente """
        def decorator(model_cls: type["ForecastModel"]):
            cls._registry[name] = model_cls
            return model_cls
        return decorator
    
    @classmethod
    def from_name(cls,model_name: str,parameters: dict[str, float],test_metrics: list[str] = ['mae','mse']) -> "ForecastModel":
        """ Método para cargar modelo de esta clase por su nombre """
        model_cls = cls._registry.get(model_name.lower())
        if model_cls is None:
            raise ValueError(
                f"Modelo desconocido '{model_name}'. Modelos disponibles: {list(cls._registry)}"
            )

        return model_cls(parameters, test_metrics)
    

    @abstractmethod
    def train(self,x_train:np.ndarray,y_train:np.ndarray)->tuple[LossHistory,Figure]|None:
        """
        Entrena modelo y regresa el historial de la función de perdida y su figura correspondiente
        Requiere ser implementado por subclases.

        Parametros:
        - x_train: array-like, Datos de entrada en cual se quieren realizar el entrenamiento del modelo.
        - y_train: array-like, Datos de entrada en cual se quieren realizar el entrenamiento del modelo.
        
        Regresa:
        - loss_history: LossHistory object, objeto que tiene almacenado el historial de perdida tanto de entrenamiento como de prueba 
        - loss_fig: matplotlib Figure object, Gráfica de perdida de entrenamiento y prueba
        """
        pass

    @abstractmethod
    def predict(self,x_test:np.ndarray,y_test:np.ndarray )->np.ndarray:
        """
        Predicciones del modelo 
        Requiere ser implementado por subclases.

        Parametros:
        - x_test: array-like, Datos de entrada en cual se quieren realizar predicciones.
        - y_test: array-like, Datos de entrada, valores reales .

        Regresa:
        - y_pred: array-like , Predicciones del modelo 
        """
        pass


    def calculate_metrics(self,y_pred:np.ndarray,y_true:np.ndarray)->Metrics:
        """
        Calcula las métricas específicadas acorde la predicción del modelo y los datos reales

        Parametros:
        - y_pred: array-like , Predicciones del modelo 
        - y_true: array-like , Datos reales

        Regresa:
        - Metrics(**result_metrics): Metrics, Resultado de los cálculos de métricas  
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
        for m in self.test_metrics:
            if m=='mae': # Mean Absolute Error
                result_metrics['mae'] = abs(y_true-y_pred).mean()

            if m=='mfe':# Mean Forecast Error
                result_metrics['mfe'] = (y_true-y_pred).mean()

            if m=='mse':# Mean Square Error
                result_metrics['mse'] = ((y_true-y_pred)**2).mean()

            if m=='da':# Directional Accuracy
                result_metrics['da'] = directional_accuracy(y_pred,y_true)
        return Metrics(**result_metrics)
    

    def plot_loss(self,loss_history:LossHistory, title:str="Loss", xlabel:str="Epochs", ylabel:str="Loss")->Figure:
        """
        Gráfica de perdida de entrenamiento y prueba
        
        Parametros:
        - loss_history: LossHistory object, objeto que tiene almacenado el historial de perdida tanto de entrenamiento como de prueba
        - title: str, Título de gráfico
        - xlabel: str, Etiqueta de eje horizontal
        - ylabel: str, Etiqueta de eje vertical
        
        Regresa:
        - fig: matplotlib Figure object
        """
        fig, ax = plt.subplots(figsize=(10,5))
        ax.plot(loss_history.train_loss, label="Train", color = 'blue')

        if hasattr(loss_history, 'test_loss') and loss_history.test_loss is not None:
            ax.plot(loss_history.test_loss, label="Test", color='orange')

        ax.set_title(title)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.legend()
        ax.grid(True)
        return fig

        
    def plot_prediction(self,y_pred:np.ndarray,y_true:np.ndarray, title:str="Prediction vs True", xlabel:str="Tiempo (días)", ylabel:str="Ventas")->Figure:
        """
        Gráfica de predicción de modelo y datos reales.
            
        Parametros:
        - y_true: array-like, Valores reales
        - y_pred: array-like, Valores predecidos
        - title: str, Título de gráfico
        - xlabel: str, Etiqueta de eje horizontal
        - ylabel: str,  Etiqueta de eje vertical

        Regresa:
        - test_fig: matplotlib Figure object, Gráfica de contraste entre predicción y datos reales

        """
        fig, ax = plt.subplots(figsize=(10,5))
        ax.plot(y_true, label="True", marker='o')
        ax.plot(y_pred, label="Predicted", marker='x')
        ax.set_title(title)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.legend()
        ax.grid(True)

        return fig
    
    def test(self,x_test:np.ndarray,y_test:np.ndarray)->tuple[Figure,Metrics]:
        """
        Gráfica de predicción de modelo y datos reales.
            
        Parametros:
        - x_test: array-like, Valores reales
        - y_test: array-like, Valores predecidos

        Regresa:
        - test_fig: matplotlib Figure object, Gráfica de contraste entre predicción y datos reales
        - metrics: Metrics , Métricas resultado de la prueba
        """
        y_pred = self.predict(x_test)
        y_true = y_test   
        metrics = self.calculate_metrics(y_pred,y_true)
        test_fig = self.plot_prediction(y_pred,y_true)
        return test_fig,metrics 


@ForecastModel.register("heuristic")
class HeuristicModel(ForecastModel):

    def get_sales_flow_index(self,dataset:pd.DataFrame)->None:
        def index(difference:int)->str:
            if difference<0:
                return "B"
            if difference==0:
                return "E"
            if difference>0:
                return "S"
        df = dataset.copy()
        max_date = df["date"].max()
        
        self.current_quatrimester = pd.date_range(end=max_date, periods=4, freq="MS").month.tolist()
        df = df[ df["month"].isin(self.current_quatrimester) ]
        df = df.sort_values("date")
        df = df[["year","month","monthly_sales"]].drop_duplicates().reset_index()
        df.loc[df.index[-1], "monthly_sales"] = self.month_estimate
        df["difference"] = df["monthly_sales"].diff().dropna().astype("int")
        df = df.dropna()
        df["index"] = df["difference"].apply(index)
        indeces = df["index"].to_list()

        self.sales_idx = ""
        for i in indeces:
            self.sales_idx += i 

    def get_client_sales(self,dataset:pd.DataFrame)->None:
        clients = get_client_list()
        client_sales = dataset.merge(clients,how="inner",on="clientId")
        if not client_sales.empty:
            client_sales["client_sales"]= client_sales.groupby(["year","month"])["quantity"].transform("sum")
            self.client_sales = client_sales[["year","month","client_sales"]].drop_duplicates()
        else: 
            self.client_sales= self.sales_period[["year","month"]]
            self.client_sales["client_sales"]=[0] * len(self.client_sales)


    def get_remaining_days(self)->None:
        self.current_day = self.sales_period["date"].max().day
        max_date = self.sales_period["date"].max()
        
        
        pass

    def fit(self,dataset:pd.DataFrame,config:ExperimentConfig|None=None)->None:
        """ 
        Cálcula las variables fundamentales para realizar predicciones de la venta mensual
        
        Parametros:
        - dataset: pandas.DataFrame , Datos con información relacionada a cada venta realizada dentro del periodo

        Regresa:
        - sales_period: pandas.DataFrame, Tabla con registro de ventas por periodo
        - sales_idx: str, Indice clasificador del flujo de ventas. Ejemplo: B-B-S
        - client_sales: pandas.DataFrame, Tabla con registro de ventas por periodo realizadas por clientes
        - current_day: int , Día más actual del periodo de entrenamiento
        - remaining_days: int , Número de días que hacen falta para terminar més de ventas

        """
        
        if config is not None:
            model_name="heuristic"
            dataset_config = DatasetFilterConfig(start_date=(config.get("training_data_start_dates")).get(model_name),
                                            end_date=(config.get("training_data_end_dates")).get(model_name),
                                            frequency=(config.get("frequencies")).get(model_name),
                                            horizon=(config.get("horizons")).get(model_name),
                                            training_window=(config.get("training_windows")).get(model_name))
        
            df = DatasetFilters(dataset_config).apply_period_filter(dataset)
        
        else :
            df = dataset.copy()

        max_date = df["date"].max()
        df["monthly_sales"] = df.groupby(["year","month"])["quantity"].transform("sum")
        self.sales_period = df[["year","month","monthly_sales"]].drop_duplicates()

        l = self.parameters['l']
        self.month_estimate =int( l*df[df["date"]==max_date]["monthly_sales"].iloc[0])

        self.get_sales_flow_index(df)

        self.get_client_sales(df)
        
        #self.get_remaining_days(df)
    
        return None
    
    def train(self, x_train: np.ndarray, y_train: np.ndarray)->None:
        """ No se tiene método de entrenamiento para este modelo actualmente"""
        history = LossHistory(train_loss=[], test_loss=[])
        fig = self.plot_loss(history)
        return None
    
    def predict(self,x_test:np.ndarray,y_test:np.ndarray)->np.ndarray|None:
        """
        Predicciones del modelo.
        Toma los datos de ventas del mes y predice la venta mensual partiendo de las ventas a mitad del periodo
        """
        l = self.parameters['l']
        pass 
        
@ForecastModel.register("arima")
class ARIMAModel(ForecastModel):
    pass