import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import calendar
import random

from scipy.stats import gaussian_kde
from mlflow.pyfunc import PythonModel
from mlops.utils import get_client_list,time_period,make_time_series,calculate_metrics,Path,ExperimentConfig,DatasetFilterConfig,DatasetFilters,Date,Metrics,DEBUG
from typing import Iterable,Any
from matplotlib.figure import Figure
from dataclasses import dataclass
from abc import ABC,abstractmethod
from statsmodels.tsa.arima.model import ARIMA



@dataclass
class LossHistory:
    train_loss:Iterable|None=None
    test_loss:Iterable|None=None

class PyfuncWrapper(PythonModel):

    def load_context(self, context):
        import pickle
        self.model = pickle.load(open(context.artifacts["model_path"], "rb"))

    def predict(self, context, model_input:np.ndarray)->np.ndarray:

        # Manejo de entradas
        if isinstance(model_input, pd.DataFrame):
            x_input = model_input.values
        elif isinstance(model_input, pd.Series):
            x_input = model_input.values.reshape(-1, 1)
        elif isinstance(model_input, np.ndarray):
            x_input = model_input
        else:
            x_input = np.array(model_input)

        return self.model.predict(x_input)
    
    def fit(self,data:pd.DataFrame,config:ExperimentConfig)->None:
        return self.model.fit(data,config)
        
class ForecastModel(ABC):
    _registry: dict[str, type["ForecastModel"]] = {}

    def __init__(self,parameters:dict[str,Any],test_metrics:list[str]=['mae','mfe','rmse','da'],seed:int|None=None,type:str|None=None,name:str|None=None):
        self.parameters= parameters
        self.test_metrics = test_metrics # Metricas que se quieren evaluar
        self.seed = seed
        self.type = type
        self.name = name

    @classmethod
    def register(cls, name: str):
        """ Decorador para registrar modelos de esta clase automáticamente """
        def decorator(model_cls: type["ForecastModel"]):
            cls._registry[name] = model_cls
            return model_cls
        return decorator
    
    @classmethod
    def from_name(cls,model_name: str,parameters: dict[str, float],test_metrics: list[str] = ['mae','rmse']) -> "ForecastModel":
        """ Método para cargar modelo de esta clase por su nombre """
        model_cls = cls._registry.get(model_name)
        if model_cls is None:
            raise ValueError(
                f"Modelo desconocido '{model_name}'. Modelos disponibles: {list(cls._registry)}"
            )

        return model_cls(parameters, test_metrics,name=model_name)
    

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

        
    def plot_prediction(self,y_pred:np.ndarray,y_true:np.ndarray, title:str="Predicción vs Real", xlabel:str="Tiempo (días)", ylabel:str="Ventas")->Figure:
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
        ax.plot(y_true, label="Real", marker='o')
        ax.plot(y_pred, label="Predicción", marker='x')
        ax.set_ylim(0)
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
        start_date = x_test.min().astype('datetime64[D]').astype(Date)
        end_date = x_test.max().astype('datetime64[D]').astype(Date)
        
        title= f"Periodo : {start_date}  /   {end_date}"
        metrics = calculate_metrics(y_pred,y_true,self.test_metrics)
        test_fig = self.plot_prediction(y_pred,y_true,title)
        return test_fig,metrics 


def load_model(model_name:str,config:ExperimentConfig|dict[str,Any])->ForecastModel:
    """
    Carga el modelo específicado

    Parametros:
    - model_name: str, Nombre del tipo de modelo siendo utilizado
    - config: ExperimentConfig , Configuración del experimento
    
    Regresa:
    - model: ForecastModel, Modelo de regresión temporal
    """
    parameters = (config.parameters)
    metrics = (config.metrics)
    model = ForecastModel.from_name(model_name=model_name,
                                    parameters=parameters,
                                    test_metrics=metrics)
    return model


@ForecastModel.register("Heuristic")
class HeuristicModel(ForecastModel):
    
    def index(self,difference:int)->str:
            if difference<0:
                return "B"
            if difference==0:
                return "E"
            if difference>0:
                return "S"
    def get_sales_flow_index(self,dataset:pd.DataFrame)->None:
        """
        Recibe el dataset del producto de analisis ( al menos 6 meses) y obtiene 
        el índice del flujo de ventas.

        Parametros:
        - dataset: pandas.DataFrame, Dataset del producto conteniendo la información de ventas en al menos 6 meses

        Regresa:
        - current_quatrimester: list[int], Lista de los últimos 4 meses del dataset analizado
        - sales_idx: str, Indice del flujo de ventas,consiste en tres siglas que describen el cambio del flujo de ventas.
                          S = Subió, E= Empató, B = Bajó
        """
        df = dataset.copy()
        max_date = df["date"].max()
        l = self.parameters['l']
        self.month_estimate =int( l*df[df["date"]==max_date]["monthly_quantity"].iloc[0])
        self.current_quatrimester = pd.date_range(end=max_date, periods=4, freq="MS").month.tolist()
        df = df[ df["month"].isin(self.current_quatrimester) ]
        df = df.sort_values("date")
        df = df[["year","month","monthly_quantity"]].drop_duplicates().reset_index()
        df.loc[df.index[-1], "monthly_quantity"] = self.month_estimate
        df["difference"] = df["monthly_quantity"].diff().dropna().astype("int")
        df = df.dropna()
        df["index"] = df["difference"].apply(self.index)
        indeces = df["index"].to_list()

        self.sales_idx = ""
        for i in indeces:
            self.sales_idx += i 

    def get_client_sales(self,dataset:pd.DataFrame)->None:
        """
        Recibe los datos de ventas del producto y regresa la cantidad de ventas realizadas por clientes.

        Parametros:
        - dataset: pandas.DataFrame, Tabla de ventas de producto en periodo de al menos 6 meses.

        Regresa:
        - client_sales: pandas.DataFrame , Tabla de la cantidad de unidades vendidas a clientes.
        """
        clients = get_client_list()
        client_sales = dataset.merge(clients,how="inner",on="clientId")
        
        if not client_sales.empty:
            self.avg_n_month_client_sales = client_sales.groupby(["year","month"]).size().mean()
            client_sales["client_sales"]= client_sales.groupby(["year","month"])["quantity"].transform("sum")
            self.client_sales = client_sales[["year","month","client_sales"]].drop_duplicates()
        else: 
            self.client_sales= self.sales_period[["year","month"]]
            self.client_sales["client_sales"]=[0] * len(self.client_sales)
            self.avg_n_month_client_sales = client_sales.groupby(["year","month"]).size().mean()
            
    def get_remaining_days(self,latest_date:pd.Timestamp)->None:
        """
        Cálcula los días restantes del último mes del periodo y los guarda cómo propiedades 
        del modelo.

        Parametros:
        - latest_date: pandas.Timestamp, Fecha del día más actual del periodo analizado

        Regresa:
        - current_day: int, Día del periodo analizado
        - current_month: int, Mes del periodo analizado
        - current_year: int, Año del periodo analizado
        - remaining_days: int, Cantidad de días restantes del último mes
        """

        self.current_day = latest_date.day
        self.current_month = latest_date.month
        self.current_year = latest_date.year

        days_in_month = calendar.monthrange(self.current_year, self.current_month)[1]
        
        self.remaining_days = days_in_month - self.current_day
    def get_month_sales(self,quatrimester_idx:int)->int:
        mask= self.sales_period["month"]==self.current_quatrimester[quatrimester_idx]
        if self.sales_period[mask].empty:
            return 0
        else:
            return int(self.sales_period[mask]["monthly_quantity"].iloc[0])

    def get_index_sum(self)->None:
        """
        Cálcula los valores de estimado ('s1','s2','s3','s4','s5') en base el índice de flujo de ventas y 
        regresa la suma total.

        Parametros:
        - : None,

        Regresa:
        - s_n: list[float], Lista de valores de ('s1','s2','s3','s4','s5')
        - idx_sum:float, Suma total de ('s1','s2','s3','s4','s5')
        """
        def s1():
            sales_period = self.sales_period
            sales_idx = self.sales_idx
            current_day = self.current_day
            month_estimate = self.month_estimate
            current_quatrimester = [ self.get_month_sales(i) for i in range(4) ]


            if sales_idx == "BES":
                if current_day <= 8:
                    if month_estimate <= current_quatrimester[0]:
                        if current_quatrimester[3] <= current_quatrimester[2]:
                            return current_quatrimester[2]
                        else:
                            return current_quatrimester[3]
                    else:
                        if current_quatrimester[3] <= current_quatrimester[2]:
                            return current_quatrimester[2]
                        else:
                            return current_quatrimester[3]

                elif current_day <= 15:
                    if month_estimate <= current_quatrimester[0]:
                        return month_estimate
                    else:
                        if current_quatrimester[3] == 1:
                            return 1
                        else:
                            return (month_estimate + current_quatrimester[0]) / 2

                elif current_day <= 21:
                    if month_estimate <= current_quatrimester[0]:
                        return month_estimate
                    else:
                        if current_quatrimester[0] <= current_quatrimester[3]:
                            return (current_quatrimester[3] + month_estimate) / 2
                        else:
                            return current_quatrimester[0]

                else:
                    if (current_quatrimester[0] + month_estimate) / 2 >= month_estimate:
                        return current_quatrimester[3]
                    else:
                        if (current_quatrimester[0] + month_estimate) / 2 >= current_quatrimester[0]:
                            return current_quatrimester[3]
                        else:
                            return (current_quatrimester[0] + month_estimate) / 2

            elif sales_idx == "BSS":
                if current_day <= 8:
                    if (current_quatrimester[2] + month_estimate) / 2 >= current_quatrimester[0]:
                        if current_quatrimester[2] >= current_quatrimester[0]:
                            return current_quatrimester[2]
                        else:
                            return current_quatrimester[0]
                    else:
                        if current_quatrimester[0] <= month_estimate:
                            return current_quatrimester[0]
                        else:
                            return (current_quatrimester[2] + month_estimate) / 2

                elif current_day <= 15:
                    max_lmn = max(current_quatrimester[0],
                                current_quatrimester[1],
                                current_quatrimester[2])

                    if month_estimate <= max_lmn:
                        return month_estimate
                    else:
                        if (current_quatrimester[0] +
                            current_quatrimester[1] +
                            month_estimate) / 3 >= month_estimate:
                            return month_estimate
                        else:
                            if (current_quatrimester[2] + month_estimate) / 2 >= current_quatrimester[3]:
                                if (current_quatrimester[2] + month_estimate) / 2 <= max_lmn:
                                    return max_lmn
                                else:
                                    return (current_quatrimester[2] + month_estimate) / 2
                            else:
                                return current_quatrimester[3]

                elif current_day <= 21:
                    return ((current_quatrimester[2] + month_estimate) / 2 + month_estimate) / 2

                else:
                    max_lmn = max(current_quatrimester[0],
                                current_quatrimester[1],
                                current_quatrimester[2])

                    if (current_quatrimester[2] + month_estimate) / 2 >= current_quatrimester[3]:
                        return (current_quatrimester[2] + month_estimate) / 2
                    else:
                        if current_quatrimester[3] <= max_lmn:
                            return current_quatrimester[3]
                        else:
                            if current_quatrimester[3] <= (2 * max_lmn):
                                return current_quatrimester[3]
                            else:
                                return (current_quatrimester[2] + month_estimate) / 2

            elif sales_idx == "EBB":
                if current_day <= 15:
                    if current_quatrimester[2] == 1:
                        return 1
                    else:
                        return (current_quatrimester[2] + month_estimate) / 2

                elif current_day <= 21:
                    if month_estimate <= (current_quatrimester[2] + month_estimate) / 2:
                        return (current_quatrimester[2] + month_estimate) / 2
                    else:
                        return month_estimate

                else:
                    return month_estimate

            elif sales_idx == "EBE":
                return current_quatrimester[2]

            else:
                return 0.0

        def s2():
            sales_period = self.sales_period
            sales_idx = self.sales_idx
            current_day = self.current_day
            month_estimate = self.month_estimate
            current_quatrimester = [ self.get_month_sales(i) for i in range(4) ]

            def count_non_zero_mn():
                return sum(1 for v in current_quatrimester[1:3] if v != 0)

            if sales_idx in ["BEE", "BBE", "BBB", "BEB"]:
                if current_day <= 8:
                    return current_quatrimester[2]

                elif current_day <= 15:
                    if month_estimate == 0:
                        if current_quatrimester[2] == 1:
                            return current_quatrimester[2]
                        else:
                            return (current_quatrimester[2] + month_estimate) / 2
                    else:
                        return (current_quatrimester[2] + month_estimate) / 2

                else:
                    if month_estimate == 0:
                        if count_non_zero_mn() == 2:
                            return month_estimate
                        else:
                            return month_estimate
                    else:
                        if current_day <= 21:
                            if (current_quatrimester[2] + current_quatrimester[3]) / 2 >= month_estimate:
                                return (current_quatrimester[2] + current_quatrimester[3]) / 2
                            else:
                                return month_estimate
                        else:
                            if sales_idx == "BEE":
                                return month_estimate
                            else:
                                if (current_quatrimester[2] + current_quatrimester[3]) / 2 <= month_estimate:
                                    return current_quatrimester[3]
                                else:
                                    return month_estimate

            elif sales_idx == "BBS":
                if current_day <= 8:
                    if current_quatrimester[3] >= current_quatrimester[1]:
                        if current_quatrimester[3] >= current_quatrimester[2]:
                            return current_quatrimester[0]
                        else:
                            return current_quatrimester[3]
                    else:
                        if current_quatrimester[2] < 0:
                            return 0
                        else:
                            if current_quatrimester[2] <= current_quatrimester[3]:
                                return current_quatrimester[3]
                            else:
                                return current_quatrimester[2]

                elif current_day <= 15:
                    max_lmn = max(current_quatrimester[0],
                                current_quatrimester[1],
                                current_quatrimester[2])

                    if month_estimate <= max_lmn:
                        if (month_estimate + current_quatrimester[2]) / 2 >= current_quatrimester[1]:
                            if current_quatrimester[1] <= current_quatrimester[3]:
                                return (month_estimate + current_quatrimester[2]) / 2
                            else:
                                return current_quatrimester[1]
                        else:
                            return (current_quatrimester[2] + month_estimate) / 2
                    else:
                        if current_quatrimester[0] == current_quatrimester[3]:
                            return (current_quatrimester[3] + month_estimate) / 2
                        else:
                            return max_lmn

                elif current_day <= 21:
                    max_lmn = max(current_quatrimester[0],
                                current_quatrimester[1],
                                current_quatrimester[2])

                    if month_estimate <= max_lmn:
                        return month_estimate
                    else:
                        if max_lmn <= current_quatrimester[3]:
                            return (current_quatrimester[3] + month_estimate) / 2
                        else:
                            return max_lmn

                else:
                    if month_estimate == 0:
                        if count_non_zero_mn() == 2:
                            if current_quatrimester[2] < 0:
                                return 0
                            else:
                                return current_quatrimester[2] / 2
                        else:
                            return month_estimate
                    else:
                        if current_quatrimester[3] >= current_quatrimester[0]:
                            if (current_quatrimester[0] + month_estimate) / 2 >= current_quatrimester[3]:
                                return (current_quatrimester[0] + month_estimate) / 2
                            else:
                                return current_quatrimester[3]
                        else:
                            return month_estimate

            elif sales_idx == "BSB":
                if current_day <= 8:
                    if month_estimate == 0:
                        if (current_quatrimester[2] + month_estimate) / 2 >= current_quatrimester[0]:
                            return (current_quatrimester[2] + month_estimate) / 2
                        else:
                            if current_quatrimester[0] >= current_quatrimester[2]:
                                return current_quatrimester[2]
                            else:
                                return current_quatrimester[0]
                    else:
                        if (current_quatrimester[2] + month_estimate) / 2 >= current_quatrimester[1]:
                            return (current_quatrimester[2] + month_estimate) / 2
                        else:
                            return current_quatrimester[1]

                elif current_day <= 15:
                    if month_estimate <= current_quatrimester[1]:
                        if month_estimate == 0:
                            if current_quatrimester[2] == current_quatrimester[0]:
                                return (current_quatrimester[0] + current_quatrimester[2]) / 2
                            else:
                                if (current_quatrimester[2] / 30) * current_day >= current_quatrimester[1]:
                                    return current_quatrimester[1]
                                else:
                                    return (current_quatrimester[2] / 30) * current_day
                        else:
                            return month_estimate
                    else:
                        return month_estimate

                elif current_day <= 21:
                    if month_estimate <= current_quatrimester[1]:
                        if current_quatrimester[3] == 0:
                            return month_estimate
                        else:
                            if current_quatrimester[1] >= current_quatrimester[3] * 2:
                                return current_quatrimester[3] * 2
                            else:
                                return current_quatrimester[1]
                    else:
                        return month_estimate

                else:
                    avg_val = (current_quatrimester[1] +
                            current_quatrimester[2] +
                            month_estimate) / 3

                    if avg_val >= month_estimate:
                        return month_estimate
                    else:
                        if month_estimate >= avg_val:
                            return month_estimate
                        else:
                            return avg_val

            elif sales_idx == "BSE":
                return current_quatrimester[2]

            else:
                return 0.0
        
        def s3():
            sales_period = self.sales_period
            sales_idx = self.sales_idx
            current_day = self.current_day
            month_estimate = self.month_estimate
            current_quatrimester = [ self.get_month_sales(i) for i in range(4) ]

            if sales_idx == "EBS":
                if current_day <= 8:
                    if (current_quatrimester[2] + month_estimate) / 2 >= current_quatrimester[1]:
                        return current_quatrimester[1]
                    else:
                        return (current_quatrimester[2] + month_estimate) / 2

                elif current_day <= 15:
                    if month_estimate <= current_quatrimester[1]:
                        return month_estimate
                    else:
                        if current_quatrimester[3] >= current_quatrimester[1]:
                            return current_quatrimester[3]
                        else:
                            return current_quatrimester[1]

                elif current_day <= 21:
                    if month_estimate <= current_quatrimester[1]:
                        return month_estimate
                    else:
                        if current_quatrimester[3] >= current_quatrimester[1]:
                            if current_quatrimester[3] <= (current_quatrimester[1] * 2):
                                return current_quatrimester[3]
                            else:
                                return (current_quatrimester[3] + current_quatrimester[1]) / 2
                        else:
                            return current_quatrimester[1]

                else:
                    if month_estimate <= current_quatrimester[1]:
                        return month_estimate
                    else:
                        return (current_quatrimester[1] + month_estimate) / 2

            elif sales_idx == "EEB":
                if current_day <= 8:
                    return current_quatrimester[0]

                elif current_day <= 15:
                    if current_quatrimester[0] == 1:
                        return 1
                    else:
                        return (current_quatrimester[0] + current_quatrimester[2]) / 2

                else:
                    if current_quatrimester[0] <= 2:
                        return 1
                    else:
                        return current_quatrimester[2]

            elif sales_idx == "EEE":
                return current_quatrimester[2]

            elif sales_idx == "EES":
                if current_day <= 8:
                    if current_quatrimester[3] >= current_quatrimester[2]:
                        if (current_quatrimester[0] +
                            current_quatrimester[1] +
                            current_quatrimester[2]) <= 0:
                            if current_quatrimester[3] == 1:
                                return 1
                            else:
                                return current_quatrimester[3] / 2
                        else:
                            return current_quatrimester[3]
                    else:
                        return current_quatrimester[2]

                elif current_day <= 15:
                    if (current_quatrimester[1] + current_quatrimester[2]) == 0:
                        return current_quatrimester[3]
                    else:
                        if current_quatrimester[3] >= current_quatrimester[2]:
                            return current_quatrimester[3]
                        else:
                            return current_quatrimester[2]

                elif current_day <= 21:
                    if current_quatrimester[2] == 0:
                        if current_quatrimester[3] <= 3:
                            return current_quatrimester[3]
                        else:
                            return current_quatrimester[3] / 2
                    else:
                        if (current_quatrimester[2] * month_estimate) / 2 <= current_quatrimester[3]:
                            return current_quatrimester[3]
                        else:
                            return (current_quatrimester[2] + month_estimate) / 2

                else:
                    if (current_quatrimester[1] + current_quatrimester[2]) == 0:
                        if current_quatrimester[3] <= 2:
                            return current_quatrimester[3]
                        else:
                            return (current_quatrimester[3] / 3) * 2
                    else:
                        return current_quatrimester[3]

            elif sales_idx in ["ESB", "SEE"]:
                if (current_quatrimester[0] + current_quatrimester[1]) <= 0:
                    if month_estimate == 0:
                        return 0
                    else:
                        if month_estimate <= (current_quatrimester[2] + month_estimate) / 2:
                            return month_estimate
                        else:
                            return (current_quatrimester[2] + month_estimate) / 2

                elif current_day <= 8:
                    if (current_quatrimester[0] + current_quatrimester[1]) <= 0:
                        if month_estimate == 0:
                            return 0
                        else:
                            if month_estimate <= (current_quatrimester[2] + month_estimate) / 2:
                                return month_estimate
                            else:
                                return (current_quatrimester[2] + month_estimate) / 2
                    else:
                        if month_estimate == 0:
                            return current_quatrimester[1]
                        else:
                            if month_estimate <= current_quatrimester[1]:
                                return month_estimate
                            else:
                                return current_quatrimester[1]

                elif current_day <= 15:
                    if month_estimate == 0:
                        return current_quatrimester[1]
                    else:
                        return month_estimate

                elif current_day <= 21:
                    return month_estimate

                else:
                    if month_estimate <= current_quatrimester[1]:
                        return month_estimate
                    else:
                        return current_quatrimester[3]

            elif sales_idx in ["ESE", "SBE"]:
                return month_estimate

            elif sales_idx == "SSE":
                return month_estimate

            else:
                return 0.0
        
        def s4():
            sales_period = self.sales_period
            sales_idx = self.sales_idx
            current_day = self.current_day
            month_estimate = self.month_estimate
            current_quatrimester = [ self.get_month_sales(i) for i in range(4) ]
            

            if sales_idx == "ESS":
                if current_day <= 8:
                    return max(current_quatrimester[2], current_quatrimester[3])

                elif current_day <= 15:
                    if current_quatrimester[3] >= current_quatrimester[2]:
                        return (current_quatrimester[2] + month_estimate) / 2
                    else:
                        return current_quatrimester[2]

                elif current_day <= 21:
                    if (current_quatrimester[2] + month_estimate) / 2 >= current_quatrimester[3]:
                        return (current_quatrimester[2] + month_estimate) / 2
                    else:
                        return current_quatrimester[3]

                else:
                    if (month_estimate + current_quatrimester[2]) / 2 >= current_quatrimester[3]:
                        return current_quatrimester[3]
                    else:
                        if month_estimate > (current_quatrimester[2] * 2):
                            if current_quatrimester[2] == 1:
                                if current_quatrimester[3] > 2:
                                    return month_estimate / 2
                                else:
                                    return month_estimate
                            else:
                                return current_quatrimester[3]
                        else:
                            return current_quatrimester[3]

            elif sales_idx == "SBB":
                if current_day < 8:
                    if current_quatrimester[3] == 0:
                        if current_quatrimester[0] <= 0:
                            return current_quatrimester[2]
                        else:
                            if current_quatrimester[2] >= min(current_quatrimester[0],
                                                            current_quatrimester[1],
                                                            current_quatrimester[2]):
                                if current_day >= 6:
                                    if current_quatrimester[0] >= current_quatrimester[2]:
                                        return current_quatrimester[2]
                                    else:
                                        return current_quatrimester[2] * 0.75
                                else:
                                    return (current_quatrimester[2] + current_quatrimester[0]) / 2
                            else:
                                return min(current_quatrimester[0],
                                        current_quatrimester[1],
                                        current_quatrimester[2])
                    else:
                        return (current_quatrimester[2] + month_estimate) / 2

                elif current_day <= 15:
                    if current_quatrimester[2] == 1:
                        return 1
                    else:
                        return (current_quatrimester[2] + month_estimate) / 2

                else:
                    return month_estimate

            elif sales_idx == "SBS":
                max_val = max(current_quatrimester[0],
                            current_quatrimester[1],
                            current_quatrimester[2])

                if current_day <= 8:
                    if max_val <= month_estimate:
                        if max_val <= current_quatrimester[3]:
                            return current_quatrimester[3]
                        else:
                            return max_val
                    else:
                        return month_estimate

                elif current_day <= 15:
                    if month_estimate <= current_quatrimester[1]:
                        return month_estimate
                    else:
                        if current_quatrimester[3] >= current_quatrimester[1]:
                            return current_quatrimester[3]
                        else:
                            return current_quatrimester[1]

                else:
                    if month_estimate <= current_quatrimester[1]:
                        return month_estimate
                    else:
                        if current_quatrimester[3] >= (2 * current_quatrimester[1]):
                            return (current_quatrimester[1] + month_estimate) / 2
                        else:
                            return current_quatrimester[3]

            elif sales_idx == "SEB":
                if current_day <= 8:
                    return current_quatrimester[2]

                elif current_day <= 15:
                    if current_quatrimester[2] == 1:
                        return 1
                    else:
                        return (current_quatrimester[2] + month_estimate) / 2

                elif current_day <= 21:
                    return month_estimate

                else:
                    if current_quatrimester[2] == 1:
                        return 1
                    else:
                        return month_estimate

            else:
                return 0.0
        
        def s5():
            sales_period = self.sales_period
            sales_idx = self.sales_idx
            current_day = self.current_day
            month_estimate = self.month_estimate
            current_quatrimester = [ self.get_month_sales(i) for i in range(4) ]
            

            if sales_idx == "SES":
                if current_day <= 8:
                    if current_quatrimester[3] >= current_quatrimester[2]:
                        return current_quatrimester[3]
                    else:
                        return current_quatrimester[2]

                elif current_day <= 15:
                    if (current_quatrimester[1] + current_quatrimester[2]) == 0:
                        return current_quatrimester[3] / 2
                    else:
                        if current_quatrimester[3] >= current_quatrimester[2]:
                            if current_quatrimester[3] == current_quatrimester[2]:
                                return (current_quatrimester[3] + month_estimate) / 2
                            else:
                                return current_quatrimester[3]
                        else:
                            return current_quatrimester[2]

                else:
                    if (current_quatrimester[1] + current_quatrimester[2]) == 0:
                        return current_quatrimester[3] / 2
                    else:
                        if (current_quatrimester[2] + month_estimate) / 2 >= current_quatrimester[3]:
                            return (current_quatrimester[2] + month_estimate) / 2
                        else:
                            if current_quatrimester[3] >= current_quatrimester[2]:
                                return current_quatrimester[3]
                            else:
                                return current_quatrimester[2]

            elif sales_idx == "SSB":
                if current_day <= 8:
                    if (current_quatrimester[2] + month_estimate) / 2 >= current_quatrimester[3]:
                        return (current_quatrimester[2] + month_estimate) / 2
                    else:
                        return current_quatrimester[3]
                else:
                    return month_estimate

            elif sales_idx == "SSS":
                if current_day <= 8:
                    return max(current_quatrimester[0],
                            current_quatrimester[1],
                            current_quatrimester[2],
                            current_quatrimester[3])

                elif current_day <= 15:
                    return (current_quatrimester[2] + month_estimate) / 2

                elif current_day <= 21:
                    if current_quatrimester[3] >= current_quatrimester[2]:
                        return (current_quatrimester[3] + month_estimate) / 2
                    else:
                        return current_quatrimester[2]

                else:
                    return current_quatrimester[3]

            else:
                return 0.0


        self.s_n = [s1(),s2(),s3(),s4(),s5()]
        self.idx_sum = s1()+s2()+s3()+s4()+s5()

    def fit(self,dataset:pd.DataFrame,config:ExperimentConfig|dict[str,Any]|None=None)->None:
        """ 
        Cálcula las variables fundamentales para realizar predicciones de la venta mensual
        
        Parametros:
        - dataset: pandas.DataFrame , Datos con información relacionada a cada venta realizada dentro del periodo

        Regresa:
        - sales_period: pandas.DataFrame, Tabla con registro de ventas por periodo
        - month_estimate: int, Estimación burda de ventas del final del més.
        - sales_idx: str, Indice clasificador del flujo de ventas. Ejemplo: B-B-S
        - client_sales: pandas.DataFrame, Tabla con registro de ventas por periodo realizadas por clientes
        - current_day: int , Día más actual del periodo de entrenamiento
        - remaining_days: int , Número de días que hacen falta para terminar més de ventas

        """
        
        if config is not None:
            if isinstance(config,ExperimentConfig):
                dataset_config = DatasetFilterConfig(start_date=config.training_data_start_date,
                                                    end_date=config.training_data_end_date,
                                                    frequency=config.frequency,
                                                    horizon=config.horizon,
                                                    training_window=config.training_window)
            
                df = DatasetFilters(dataset_config).apply_period_filter(dataset)

            else:
                dataset_config = DatasetFilterConfig(start_date=(config.get("training_data_start_date")),
                                                    end_date=(config.get("training_data_end_date")),
                                                    frequency=(config.get("frequency")),
                                                    horizon=(config.get("horizon")),
                                                    training_window=(config.get("training_window")))
            
                df = DatasetFilters(dataset_config).apply_period_filter(dataset)
        
        else :
            df = dataset.copy()
        
        max_date = df["date"].max()
        df["monthly_quantity"] = df.groupby(["year","month"])["quantity"].transform("sum")
        
        
        self.avg_n_month_sales = df.groupby(["year","month"]).size().mean()
        self.sales_period = df[["year","month","monthly_quantity"]].drop_duplicates()
    
        

        self.get_sales_flow_index(df)

        self.get_client_sales(df)

        self.get_remaining_days(max_date)

        self.get_index_sum()
    
        return None
    
    def train(self, x_train: np.ndarray, y_train: np.ndarray)->None:
        """ No se tiene método de entrenamiento para este modelo actualmente"""
        history = LossHistory(train_loss=[], test_loss=[])
        fig = self.plot_loss(history)
        return None
    
    def predict_next_month_sale(self)->int|None:
        """
        Predicciones del modelo.
        Toma los datos de ventas del mes y predice la venta mensual partiendo de las ventas a mitad del periodo
        """
        

        l = self.parameters['l']
        
        # Estimación ideal
        sales_condition = sum(1 for s in self.sales_period["monthly_quantity"].to_list() if s >= 1) > 2
        client_sales_condition = sum(1 for c in self.client_sales["client_sales"].to_list() if c >= 2) >= 1 
        if sales_condition or client_sales_condition:
            first_estimate = self.idx_sum
        else:
            first_estimate = 0

        # Estimación ajustada
        if self.remaining_days == 0:
            adjusted_estimate = 0
        else:
            if self.remaining_days < 30:
                if first_estimate < 6:
                    adjusted_estimate = first_estimate
                else:
                    adjusted_estimate = int(first_estimate * (self.remaining_days / 30))
            else:
                adjusted_estimate = int(first_estimate * (self.remaining_days / 30))

        # Estimación definitiva
        if adjusted_estimate == 0:
            final_estimate = 0
        elif adjusted_estimate < 0:
            final_estimate = 0
        elif adjusted_estimate < 0.5:
            final_estimate = first_estimate
        else:
            final_estimate = adjusted_estimate

        return final_estimate   
    
    def generate_sales_data(self,n_samples:int,start_date:Date,end_date:Date,client_sales:bool=False)->pd.DataFrame:
        """
        Genera datos sintéticos en base a distribución observada por datos de ventas

        Parametros:
        - n_samples: int, Cantidad de valores que se quieren generar
        - start_date: Date, Fecha inicio de periodo de registros
        - end_date: Date, Fecha fin de periodo registros
        - client_sales: bool, Determina si se quieren generar ventas normales o ventas de cliente

        Regresa: 
        - df: pandas.DataFrame, Datos generados 

        """
        if self.seed is not None:
            random.seed(self.seed)
        if client_sales:
            new_data = self.client_sales_distribution.resample(size=n_samples)[0]
        else:
            new_data = self.distribution.resample(size=n_samples)[0]

        period = time_period(start_date,end_date)

        random_dates = [random.choice(period) for _ in range(n_samples)]
        df = pd.DataFrame({
                            "date": random_dates,
                            "quantity": new_data
                        })
        df["date"] = pd.to_datetime(df["date"])
        df["month"] = df["date"].dt.month
        df["year"] = df["date"].dt.year

        df["monthly_quantity"] = df.groupby(["year","month"])["quantity"].transform("sum")
        
        return  df
    

        
    def predict(self,x_input:np.ndarray)->np.ndarray:
        
        df = self.sales_period.copy()
        max_date = df["date"].max()
        

        max_date = df["date"].max()
        max_input_date = pd.to_datetime(x_input.max())       
        min_input_date = pd.to_datetime(x_input.min())        
        n_of_months = (
                max_input_date.to_period("M") - min_input_date.to_period("M")
            ).n
        months_to_estimate = pd.date_range(end=max_input_date, periods=n_of_months, freq="MS").month.tolist()

        if max_date >= max_input_date:

            mask = df["month"].isin(months_to_estimate)
            return df[mask]["monthly_quantity"].to_numpy()

        # Generar datos de ventas hasta última fecha de predicción
        synthetic_sales = self.generate_sales_data(n_samples=self.avg_n_month_sales,
                                                   start_date=Date(max_date),
                                                   end_date=x_input.max())
        
        synthetic_client_sales = self.generate_sales_data(n_samples=self.avg_n_month_client_sales,
                                                   start_date=Date(max_date),
                                                   end_date=x_input.max(),
                                                   client_sales=True)
        
        
        l = self.parameters['l']

        for m in months_to_estimate:
            tmp_sales = synthetic_sales[synthetic_sales["month"]==m]
            tmp_client_sales = synthetic_client_sales[synthetic_client_sales["month"]==m]
            tmp_df = pd.concat([df,
                                tmp_sales,
                                tmp_client_sales])
            
            tmp_df["monthly_quantity"] = tmp_df.groupby(["year","month"])["monthly_quantity"].transform("sum")
            tmp_max_date = tmp_df["date"].max()

            self.month_estimate =int( l*tmp_df["monthly_quantity"].iloc[0])
            self.current_quatrimester = pd.date_range(end=tmp_max_date, periods=4, freq="MS").month.tolist()
            
            # Índice de flujo
            tmp_df = tmp_df[["year","month","monthly_quantity"]].drop_duplicates().reset_index()
            tmp_df.loc[tmp_df.index[-1], "monthly_quantity"] = self.month_estimate
            tmp_df["difference"] = tmp_df["monthly_quantity"].diff().dropna().astype("int")
            tmp_df = tmp_df.dropna()
            tmp_df["index"] = tmp_df["difference"].apply(self.index)
            indeces = tmp_df["index"].to_list()

            self.sales_idx = ""
            for i in indeces:
                self.sales_idx += i 
            
            # Ventas de Cliente
            tmp_client_sales["client_sales"]= tmp_client_sales.groupby(["year","month"])["monthly_quantity"].transform("sum")
            self.client_sales = tmp_client_sales[["year","month","client_sales"]].drop_duplicates()
        
            self.get_remaining_days(tmp_max_date)

            self.get_index_sum()

            prediction = self.predict_next_month_sale()

            # Actualización
            next_month = (m)%12+1
            next_year = self.current_year+1 if next_month==1 else self.current_year 
            new_row = {"year":next_year,"month":next_month,"monthly_quantity":prediction}

            self.sales_period = pd.concat([self.sales_period,pd.DataFrame(new_row)])

            df = self.sales_period.copy()

        return df[df["month"].isin(months_to_estimate)]["monthly_quantity"].to_numpy() 




@ForecastModel.register("ARIMA")
class ARIMAModel(ForecastModel):

    def fit(self,dataset:pd.DataFrame,config:ExperimentConfig|None=None)->None:
        p = self.parameters.get('p')
        d = self.parameters.get('d')
        q = self.parameters.get('q')

        df = dataset.copy()
        if config is None:
            target_column = "quantity"
            training_window = 100
            horizon = 30
            start_date = pd.to_datetime(Date(2024,9,1))
            end_date = pd.to_datetime(Date(2025,2,5))
            period = time_period(start_date=start_date,end_date=end_date)

        # Frecuencía
        else:
            if config.frequency == "daily":
                target_column = "quantity"

            if config.frequency == "weekly":
                df["weekly_quantity"]=df.groupby(["year","week"])["quantity"].transform("sum")
                target_column="weekly_quantity"

            if config.frequency == "monthly": 
                df["monthly_quantity"]=df.groupby(["year","month"])["quantity"].transform("sum")
                target_column="monthly_quantity"

            # 
            training_window = config.training_window
            horizon = config.horizon
        
            if config.training_data_start_date == "oldest":
                start_date = pd.to_datetime( dataset['date'].min())
            else:
                start_date = pd.to_datetime(config.training_data_start_date)

            if config.training_data_end_date == "latest":
                end_date = pd.to_datetime( dataset['date'].max())
            else:
                end_date = pd.to_datetime(config.training_data_end_date)
            
            period = time_period(start_date=start_date,end_date=end_date)

        x,y = make_time_series(df,period,target_column)

        if len(y)< horizon+training_window :
            print(f"Dataset invalido: Insuficiente datos para configuración actual.\nNúmero de datos:{len(y)}\nNúmero Requerido:{horizon+training_window}")
            return None
        
        x_train = x[:training_window]
        y_train = y[:training_window]
        if DEBUG:
            print(f"{start_date}-{end_date}")
            print(f"Dataset:{dataset}")
            print(f"Entrenamiento:{y_train}")
            print(f"Prueba:{y[training_window:training_window+horizon]}")
        self.known_data = pd.Series(y_train,index=x_train)

        self.mean = y_train.mean()
        self.std = y_train.std()
        if self.std == 0:
            self.std = 1
        y_scaled = (y_train - self.mean) / self.std
        
        model = ARIMA(y_train,
              order=(p, d, q), # p,d,q
              enforce_stationarity=True,
              enforce_invertibility=True)
        
        self.fitted_model = model.fit(method_kwargs={"maxiter": 1000})
        self.model = self.fitted_model

    def predict(self,x_input:np.ndarray)->np.ndarray:
        known_data = self.known_data 
        known_outputs = known_data[known_data.index.isin(x_input)].to_numpy()

        n_steps = len(x_input)-len(known_outputs)
        if n_steps >0:
            forecast_res = self.fitted_model.get_forecast(steps=n_steps)

            # Escalamiento
            
            forecast = forecast_res.predicted_mean
            #forecast = forecast*self.std + self.mean
            conf = forecast_res.conf_int()
            #conf = conf * self.std + self.mean
            predicted_values = forecast

            if isinstance(conf, np.ndarray):
                conf = pd.DataFrame(conf, columns=["lower", "upper"])

            if isinstance(forecast, np.ndarray):
                forecast = pd.Series(forecast)

            conf.index = forecast.index

            self.confidence_int_lower_series = conf.iloc[:, 0]
            self.confidence_int_upper_series = conf.iloc[:, 1]
            y_pred = np.concatenate((known_outputs, predicted_values), axis=0)
        else:
            y_pred=known_outputs

        return y_pred


    def train(self,x_train:np.ndarray,y_train:np.ndarray):
        return None
    
    def plot_prediction(self,y_pred:np.ndarray,y_true:np.ndarray, title:str="Predicción vs Real", xlabel:str="Tiempo (días)", ylabel:str="Ventas")->Figure:
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
        ax.plot(y_true, label="Real", marker='o')
        ax.plot(y_pred, label="Predicción", marker='x')
        ax.fill_between(
                        self.confidence_int_lower_series.index,
                        self.confidence_int_lower_series,
                        self.confidence_int_upper_series,
                        color='k',
                        alpha=0.15
                    )
        ax.set_ylim(0)
        ax.set_title(title)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.legend()
        ax.grid(True)

        return fig
    
    def save(self, path:Path):
        import pickle
        with open(path, "wb") as f:
            pickle.dump(self, f)

    @classmethod
    def load(cls, path: Path):
        import pickle
        with open(path, "rb") as f:
            return pickle.load(f)    