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
    """
    Almacena el historial de la función de pérdida durante el entrenamiento.

    Attributes
    ----------
    train_loss : Iterable or None
        Secuencia de valores de pérdida registrados en cada época de
        entrenamiento. Por defecto None.
    test_loss : Iterable or None
        Secuencia de valores de pérdida registrados en cada época de
        validación o prueba. Por defecto None.
    """
    train_loss:Iterable|None=None
    test_loss:Iterable|None=None

class PyfuncWrapper(PythonModel):
    """
    Envuelve un modelo serializado con pickle para su uso dentro del
    framework MLflow como PythonModel.

    Carga el modelo desde un artefacto al inicializar el contexto y
    expone métodos estándar de predicción, entrenamiento y ajuste
    compatibles con la interfaz de MLflow.

    Methods
    -------
    load_context(context)
        Deserializa el modelo desde el artefacto registrado en MLflow.
    predict(context, model_input)
        Genera predicciones a partir del modelo cargado.
    fit(data, config)
        Delega el entrenamiento al modelo interno.
    """
    def load_context(self, context):
        """
        Deserializa y carga el modelo desde el artefacto MLflow.

        Parameters
        ----------
        context : mlflow.pyfunc.PythonModelContext
            Contexto de MLflow que contiene la ruta del artefacto bajo la
            clave `'model_path'`.

        Returns
        -------
        None
        """
        import pickle
        self.model = pickle.load(open(context.artifacts["model_path"], "rb"))

    def predict(self, context, model_input:np.ndarray)->np.ndarray:
        """
        Genera predicciones del modelo cargado a partir de la entrada dada.

        Normaliza la entrada a `np.ndarray` independientemente de si se
        recibe como `pd.DataFrame`, `pd.Series`, `np.ndarray` u otro tipo.

        Parameters
        ----------
        context : mlflow.pyfunc.PythonModelContext
            Contexto de MLflow (no utilizado directamente en este método).
        model_input : array-like
            Datos de entrada. Puede ser `pd.DataFrame`, `pd.Series`,
            `np.ndarray` o cualquier tipo convertible a array.

        Returns
        -------
        np.ndarray
            Predicciones generadas por el modelo interno.
        """
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
        """
        Delega el ajuste del modelo al modelo interno encapsulado.

        Parameters
        ----------
        data : pd.DataFrame
            Datos de entrenamiento.
        config : ExperimentConfig
            Configuración del experimento con parámetros de entrenamiento.

        Returns
        -------
        None
        """
        return self.model.fit(data,config)
        
class ForecastModel(ABC):
    """
    Clase base abstracta para modelos de pronóstico de series de tiempo.

    Define la interfaz común de entrenamiento, predicción, visualización
    y registro de subclases. Mantiene un registro interno de modelos
    disponibles mediante el decorador `register`.

    Parameters
    ----------
    parameters : dict of str to Any
        Hiperparámetros del modelo.
    test_metrics : list of str, optional
        Lista de métricas a evaluar durante la prueba. Valores válidos:
        `'mae'`, `'mfe'`, `'rmse'`, `'da'`. Por defecto
        `['mae', 'mfe', 'rmse', 'da']`.
    seed : int or None, optional
        Semilla para reproducibilidad. Por defecto None.
    type : str or None, optional
        Tipo o familia del modelo. Por defecto None.
    name : str or None, optional
        Nombre identificador del modelo. Por defecto None.

    Attributes
    ----------
    _registry : dict of str to type
        Registro de clase que mapea nombres a subclases de `ForecastModel`.
    parameters : dict
    test_metrics : list of str
    seed : int or None
    type : str or None
    name : str or None

    Methods
    -------
    register(name)
        Decorador de clase para registrar subclases por nombre.
    from_name(model_name, parameters, test_metrics)
        Instancia un modelo registrado por su nombre.
    train(x_train, y_train)
        Entrena el modelo. Debe implementarse en subclases.
    predict(x_test, y_test)
        Genera predicciones. Debe implementarse en subclases.
    plot_loss(loss_history, title, xlabel, ylabel)
        Grafica el historial de pérdida de entrenamiento y prueba.
    plot_prediction(y_pred, y_true, title, xlabel, ylabel)
        Grafica la predicción frente a los valores reales.
    test(x_test, y_test)
        Evalúa el modelo y genera métricas y figura de predicción.
    """
    _registry: dict[str, type["ForecastModel"]] = {}

    def __init__(self,parameters:dict[str,Any],test_metrics:list[str]=['mae','mfe','rmse','da'],seed:int|None=None,type:str|None=None,name:str|None=None):
        self.parameters= parameters
        self.test_metrics = test_metrics # Metricas que se quieren evaluar
        self.seed = seed
        self.type = type
        self.name = name

    @classmethod
    def register(cls, name: str):
        """
        Decorador de clase para registrar subclases de ForecastModel por nombre.

        Parameters
        ----------
        name : str
            Nombre clave bajo el cual se registra la subclase en `_registry`.

        Returns
        -------
        decorator : callable
            Función decoradora que registra la clase y la retorna sin modificarla.
        """
        def decorator(model_cls: type["ForecastModel"]):
            cls._registry[name] = model_cls
            return model_cls
        return decorator
    
    @classmethod
    def from_name(cls,model_name: str,parameters: dict[str, float],test_metrics: list[str] = ['mae','rmse']) -> "ForecastModel":
        """
        Instancia un modelo registrado a partir de su nombre.

        Parameters
        ----------
        model_name : str
            Nombre del modelo tal como fue registrado con `@ForecastModel.register`.
        parameters : dict of str to float
            Hiperparámetros a pasar al constructor del modelo.
        test_metrics : list of str, optional
            Métricas de evaluación a usar durante la prueba.
            Por defecto `['mae', 'rmse']`.

        Returns
        -------
        ForecastModel
            Instancia del modelo correspondiente al nombre dado.

        Raises
        ------
        ValueError
            Si `model_name` no corresponde a ningún modelo registrado en
            `_registry`.
        """
        model_cls = cls._registry.get(model_name)
        if model_cls is None:
            raise ValueError(
                f"Modelo desconocido '{model_name}'. Modelos disponibles: {list(cls._registry)}"
            )

        return model_cls(parameters, test_metrics,name=model_name)
    

    @abstractmethod
    def train(self,x_train:np.ndarray,y_train:np.ndarray)->tuple[LossHistory,Figure]|None:
        """
        Entrena el modelo con los datos proporcionados.

        Debe ser implementado por cada subclase concreta.

        Parameters
        ----------
        x_train : np.ndarray
            Datos de entrada para el entrenamiento.
        y_train : np.ndarray
            Valores objetivo para el entrenamiento.

        Returns
        -------
        tuple of (LossHistory, matplotlib.figure.Figure) or None
            `LossHistory` con el historial de pérdida de entrenamiento y
            prueba, y la figura correspondiente. Puede retornar None si el
            modelo no tiene proceso de entrenamiento iterativo.
        """
        pass

    @abstractmethod
    def predict(self,x_test:np.ndarray,y_test:np.ndarray )->np.ndarray:
        """
        Genera predicciones sobre los datos de prueba.

        Debe ser implementado por cada subclase concreta.

        Parameters
        ----------
        x_test : np.ndarray
            Datos de entrada sobre los cuales se realizan las predicciones.
        y_test : np.ndarray
            Valores reales del período de prueba.

        Returns
        -------
        np.ndarray
            Predicciones generadas por el modelo.
        """
        pass


    

    def plot_loss(self,loss_history:LossHistory, title:str="Loss", xlabel:str="Epochs", ylabel:str="Loss")->Figure:
        """
        Genera una gráfica del historial de pérdida de entrenamiento y prueba.

        Parameters
        ----------
        loss_history : LossHistory
            Objeto con los historiales `train_loss` y `test_loss` a graficar.
        title : str, optional
            Título de la gráfica. Por defecto `'Loss'`.
        xlabel : str, optional
            Etiqueta del eje horizontal. Por defecto `'Epochs'`.
        ylabel : str, optional
            Etiqueta del eje vertical. Por defecto `'Loss'`.

        Returns
        -------
        matplotlib.figure.Figure
            Figura con las curvas de pérdida de entrenamiento y, si existe,
            de prueba.
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
        Genera una gráfica de contraste entre los valores predichos y los reales.

        Parameters
        ----------
        y_pred : np.ndarray
            Valores predichos por el modelo.
        y_true : np.ndarray
            Valores reales observados.
        title : str, optional
            Título de la gráfica. Por defecto `'Predicción vs Real'`.
        xlabel : str, optional
            Etiqueta del eje horizontal. Por defecto `'Tiempo (días)'`.
        ylabel : str, optional
            Etiqueta del eje vertical. Por defecto `'Ventas'`.

        Returns
        -------
        matplotlib.figure.Figure
            Figura con las series de valores reales y predichos superpuestas.
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
        Evalúa el modelo sobre el conjunto de prueba y genera métricas y figura.

        Realiza las predicciones con `predict`, calcula las métricas
        configuradas en `self.test_metrics` y genera la gráfica de
        predicción con el rango de fechas del período evaluado como título.

        Parameters
        ----------
        x_test : np.ndarray
            Fechas o índices temporales del conjunto de prueba.
        y_test : np.ndarray
            Valores reales del conjunto de prueba.

        Returns
        -------
        test_fig : matplotlib.figure.Figure
            Figura de contraste entre predicciones y valores reales.
        metrics : Metrics
            Objeto con los valores calculados para cada métrica en
            `self.test_metrics`.
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
    Instancia el modelo de pronóstico especificado con la configuración dada.

    Parameters
    ----------
    model_name : str
        Nombre del modelo registrado en `ForecastModel._registry`.
    config : ExperimentConfig or dict of str to Any
        Configuración del experimento. Se usan los campos `parameters`
        y `metrics` para instanciar el modelo.

    Returns
    -------
    ForecastModel
        Instancia del modelo solicitado con los parámetros e métricas
        extraídos de `config`.
    """
    parameters = (config.parameters)
    metrics = (config.metrics)
    model = ForecastModel.from_name(model_name=model_name,
                                    parameters=parameters,
                                    test_metrics=metrics)
    return model


@ForecastModel.register("Heuristic")
class HeuristicModel(ForecastModel):
    """
    Modelo heurístico de pronóstico de ventas mensuales basado en el
    índice de flujo de ventas.

    Clasifica el comportamiento reciente de las ventas en un índice de
    tres caracteres (e.g. `'BSS'`, `'EES'`) formado por la combinación
    de `'B'` (bajó), `'E'` (empató) y `'S'` (subió), y aplica reglas
    deterministas sobre el cuatrimestre actual para estimar la venta del
    mes en curso y los meses futuros.

    Parameters
    ----------
    parameters : dict of str to Any
        Hiperparámetros del modelo. Debe contener la clave `'l'` que
        representa el factor de escala para la estimación mensual.
    test_metrics : list of str, optional
        Métricas de evaluación. Por defecto `['mae', 'mfe', 'rmse', 'da']`.
    seed : int or None, optional
        Semilla para reproducibilidad en generación de datos sintéticos.
    type : str or None, optional
        Tipo del modelo.
    name : str or None, optional
        Nombre del modelo.

    Attributes
    ----------
    sales_period : pd.DataFrame
        Tabla con ventas mensuales del período de entrenamiento.
    month_estimate : int
        Estimación de ventas del mes actual basada en el factor `l`.
    sales_idx : str
        Índice de flujo de ventas de tres caracteres.
    client_sales : pd.DataFrame
        Ventas mensuales realizadas por clientes registrados.
    current_day : int
        Día más reciente del período de entrenamiento.
    current_month : int
        Mes más reciente del período de entrenamiento.
    current_year : int
        Año más reciente del período de entrenamiento.
    remaining_days : int
        Días restantes del mes en curso al momento del último dato.
    current_quatrimester : list of int
        Últimos 4 meses del período analizado.
    s_n : list of float
        Valores individuales de los cinco estimadores `s1`–`s5`.
    idx_sum : float
        Suma total de los cinco estimadores.
    avg_n_month_sales : float
        Promedio de registros de venta por mes.
    avg_n_month_client_sales : float
        Promedio de registros de venta por mes de clientes.

    Methods
    -------
    get_sales_flow_index(dataset)
        Calcula el índice de flujo de ventas y el cuatrimestre actual.
    get_client_sales(dataset)
        Calcula las ventas mensuales de clientes registrados.
    get_remaining_days(latest_date)
        Calcula los días restantes del mes en curso.
    get_month_sales(quatrimester_idx)
        Retorna las ventas del mes indicado en el cuatrimestre actual.
    get_index_sum()
        Calcula los estimadores `s1`–`s5` y su suma total.
    fit(dataset, config)
        Ajusta el modelo calculando todas las variables fundamentales.
    train(x_train, y_train)
        Sin implementación activa para este modelo.
    predict_next_month_sale()
        Predice las ventas del próximo mes.
    generate_sales_data(n_samples, start_date, end_date, client_sales)
        Genera datos sintéticos de ventas.
    predict(x_input)
        Genera predicciones para el rango de fechas proporcionado.
    """
    def index(self,difference:int)->str:
            if difference<0:
                return "B"
            if difference==0:
                return "E"
            if difference>0:
                return "S"
    def get_sales_flow_index(self,dataset:pd.DataFrame)->None:
        """
        Calcula el índice de flujo de ventas y el cuatrimestre actual.

        Analiza los últimos cuatro meses del dataset para construir un
        índice de tres caracteres que describe la tendencia de las ventas
        (`'S'` subió, `'E'` empató, `'B'` bajó). Guarda los resultados
        como atributos del modelo.

        Parameters
        ----------
        dataset : pd.DataFrame
            Datos de ventas del producto con al menos 6 meses de historia.
            Debe contener las columnas `date`, `month`, `year` y
            `monthly_quantity`.

        Returns
        -------
        None

        Notes
        -----
        Modifica los atributos `self.month_estimate`, `self.current_quatrimester`
        y `self.sales_idx` directamente sobre la instancia.
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
        Calcula las ventas mensuales realizadas por clientes registrados.

        Cruza el dataset de ventas con la lista de clientes obtenida de
        `get_client_list()` y agrega las unidades vendidas por mes. Si no
        hay coincidencias, inicializa las ventas de cliente en cero.
        Guarda los resultados como atributos del modelo.

        Parameters
        ----------
        dataset : pd.DataFrame
            Datos de ventas del producto. Debe contener las columnas
            `clientId`, `year`, `month` y `quantity`.

        Returns
        -------
        None

        Notes
        -----
        Modifica los atributos `self.client_sales` y
        `self.avg_n_month_client_sales` directamente sobre la instancia.
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
        Calcula los días restantes del mes en curso a partir de la fecha más reciente.

        Parameters
        ----------
        latest_date : pd.Timestamp
            Fecha más actual del período analizado.

        Returns
        -------
        None

        Notes
        -----
        Modifica los atributos `self.current_day`, `self.current_month`,
        `self.current_year` y `self.remaining_days` directamente sobre
        la instancia.
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
        Calcula los cinco estimadores heurísticos y su suma total.

        Evalúa las funciones internas `s1` a `s5`, cada una responsable de
        un subconjunto de patrones del índice de flujo de ventas, y almacena
        sus resultados como atributos del modelo.

        Returns
        -------
        None

        Notes
        -----
        Modifica los atributos `self.s_n` (lista con los valores de cada
        estimador) y `self.idx_sum` (suma total) directamente sobre la
        instancia. Cada función interna `s1`–`s5` cubre un conjunto
        disjunto de valores del índice `self.sales_idx`.
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
        Ajusta el modelo calculando todas las variables fundamentales para
        el pronóstico.

        Si se proporciona `config`, filtra el dataset al período de
        entrenamiento especificado. Luego calcula el índice de flujo de
        ventas, las ventas de clientes, los días restantes del mes y los
        estimadores heurísticos.

        Parameters
        ----------
        dataset : pd.DataFrame
            Datos de ventas del producto. Debe contener las columnas `date`,
            `year`, `month` y `quantity`.
        config : ExperimentConfig or dict of str to Any or None, optional
            Configuración del experimento con parámetros de filtrado temporal
            (`training_data_start_date`, `training_data_end_date`,
            `frequency`, `horizon`, `training_window`). Si es None, se
            utiliza el dataset completo sin filtrar. Por defecto None.

        Returns
        -------
        None

        Notes
        -----
        Establece los atributos `sales_period`, `month_estimate`,
        `sales_idx`, `client_sales`, `current_day`, `current_month`,
        `current_year`, `remaining_days`, `s_n` e `idx_sum`.
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
        Predice las ventas del siguiente mes a partir del estado actual del modelo.

        Calcula una estimación en tres etapas: estimación ideal basada en
        `idx_sum`, estimación ajustada proporcionalmente a los días
        restantes del mes, y estimación definitiva con correcciones de
        borde para valores pequeños o negativos.

        Returns
        -------
        int or None
            Cantidad estimada de unidades a vender en el próximo mes.
            Retorna `0` si no se cumplen las condiciones mínimas de venta
            o si los días restantes son cero.
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
        Genera datos sintéticos de ventas remuestreando la distribución observada.

        Parameters
        ----------
        n_samples : int
            Número de registros de venta a generar.
        start_date : Date
            Fecha de inicio del período de los registros generados.
        end_date : Date
            Fecha de fin del período de los registros generados.
        client_sales : bool, optional
            Si es True, remuestrea desde `self.client_sales_distribution`.
            Si es False, remuestrea desde `self.distribution`. Por defecto False.

        Returns
        -------
        pd.DataFrame
            DataFrame con columnas `date`, `quantity`, `month`, `year` y
            `monthly_quantity`, con fechas asignadas aleatoriamente dentro
            del período especificado.
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
    """
    Modelo ARIMA para pronóstico de series de tiempo de ventas.

    Ajusta un modelo ARIMA(p, d, q) sobre los datos de entrenamiento
    escalados (media cero, varianza unitaria) y genera predicciones
    hacia adelante con intervalos de confianza.

    Parameters
    ----------
    parameters : dict of str to Any
        Hiperparámetros del modelo. Debe contener las claves `'p'`, `'d'`
        y `'q'` correspondientes al orden del modelo ARIMA.
    test_metrics : list of str, optional
        Métricas de evaluación. Por defecto `['mae', 'mfe', 'rmse', 'da']`.
    seed : int or None, optional
        Semilla para reproducibilidad. Por defecto None.
    type : str or None, optional
        Tipo del modelo. Por defecto None.
    name : str or None, optional
        Nombre del modelo. Por defecto None.

    Attributes
    ----------
    known_data : pd.Series
        Serie temporal de entrenamiento indexada por fechas.
    mean : float
        Media de los datos de entrenamiento usada para escalar.
    std : float
        Desviación estándar de los datos de entrenamiento usada para escalar.
    fitted_model : statsmodels ARIMAResults
        Modelo ARIMA ajustado.
    confidence_int_lower_series : pd.Series
        Límite inferior del intervalo de confianza de las predicciones.
    confidence_int_upper_series : pd.Series
        Límite superior del intervalo de confianza de las predicciones.

    Methods
    -------
    fit(dataset, config)
        Ajusta el modelo ARIMA sobre los datos de entrenamiento.
    predict(x_input)
        Genera predicciones para el rango de fechas proporcionado.
    train(x_train, y_train)
        Sin implementación activa para este modelo.
    plot_prediction(y_pred, y_true, title, xlabel, ylabel)
        Grafica predicción con intervalo de confianza.
    save(path)
        Serializa el modelo a disco con pickle.
    load(path)
        Deserializa un modelo desde disco.
    """
    def fit(self,dataset:pd.DataFrame,config:ExperimentConfig|None=None)->None:
        """
        Ajusta el modelo ARIMA sobre los datos de entrenamiento.

        Prepara la serie temporal según la frecuencia configurada (diaria,
        semanal o mensual), escala los datos y ajusta el modelo ARIMA con
        los órdenes `p`, `d`, `q` definidos en `self.parameters`.

        Parameters
        ----------
        dataset : pd.DataFrame
            Datos de ventas del producto. Debe contener las columnas `date`,
            `quantity`, `year`, `month` y opcionalmente `week`.
        config : ExperimentConfig or None, optional
            Configuración del experimento con los campos `frequency`,
            `training_window`, `horizon`, `training_data_start_date` y
            `training_data_end_date`. Si es None, usa valores por defecto
            de desarrollo. Por defecto None.

        Returns
        -------
        None

        Notes
        -----
        Si el dataset no tiene suficientes registros para cubrir
        `training_window + horizon`, imprime un aviso y retorna None
        sin ajustar el modelo.
        """
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
        
        model = ARIMA(y_scaled,
              order=(p, d, q), # p,d,q
              enforce_stationarity=True,
              enforce_invertibility=True)
        
        self.fitted_model = model.fit(method_kwargs={"maxiter": 1000})
        self.model = self.fitted_model

    def predict(self,x_input:np.ndarray)->np.ndarray:
        """
        Genera predicciones para el rango de fechas proporcionado.

        Reutiliza los valores conocidos de entrenamiento para fechas dentro
        de `known_data` y genera pronósticos hacia adelante con el modelo
        ajustado para las fechas restantes. Revierte el escalado antes de
        retornar los valores.

        Parameters
        ----------
        x_input : np.ndarray
            Array de fechas para las cuales se desean predicciones.

        Returns
        -------
        np.ndarray
            Valores predichos para cada fecha en `x_input`, combinando
            datos conocidos y pronósticos futuros desescalados.

        Notes
        -----
        Actualiza los atributos `self.confidence_int_lower_series` y
        `self.confidence_int_upper_series` con los intervalos de confianza
        de los pasos pronosticados.
        """
        known_data = self.known_data 
        known_outputs = known_data[known_data.index.isin(x_input)].to_numpy()

        n_steps = len(x_input)-len(known_outputs)
        if n_steps >0:
            forecast_res = self.fitted_model.get_forecast(steps=n_steps)

            # Escalamiento
            
            forecast = forecast_res.predicted_mean
            forecast = forecast*self.std + self.mean
            conf = forecast_res.conf_int()
            conf = conf * self.std + self.mean
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
        Genera una gráfica de predicción frente a valores reales con
        intervalo de confianza sombreado.

        Extiende `ForecastModel.plot_prediction` añadiendo una banda
        sombreada entre `confidence_int_lower_series` y
        `confidence_int_upper_series`.

        Parameters
        ----------
        y_pred : np.ndarray
            Valores predichos por el modelo.
        y_true : np.ndarray
            Valores reales observados.
        title : str, optional
            Título de la gráfica. Por defecto `'Predicción vs Real'`.
        xlabel : str, optional
            Etiqueta del eje horizontal. Por defecto `'Tiempo (días)'`.
        ylabel : str, optional
            Etiqueta del eje vertical. Por defecto `'Ventas'`.

        Returns
        -------
        matplotlib.figure.Figure
            Figura con las series de valores reales y predichos, más la
            banda de intervalo de confianza.
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
        """
        Serializa el modelo a disco usando pickle.

        Parameters
        ----------
        path : Path
            Ruta del archivo de destino donde se guardará el modelo.

        Returns
        -------
        None
        """
        import pickle
        with open(path, "wb") as f:
            pickle.dump(self, f)

    @classmethod
    def load(cls, path: Path):
        """
        Deserializa un modelo ARIMAModel desde disco.

        Parameters
        ----------
        path : Path
            Ruta del archivo pickle que contiene el modelo serializado.

        Returns
        -------
        ARIMAModel
            Instancia del modelo cargada desde el archivo.
        """
        import pickle
        with open(path, "rb") as f:
            return pickle.load(f)    