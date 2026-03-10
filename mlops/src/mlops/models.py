import numpy as np
import matplotlib.pyplot as plt
from typing import Iterable
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
    def __init__(self,parameters:dict[str,float],test_metrics:list[str]=['mae','mse']):
        self.parameters= parameters
        self.test_metrics = test_metrics # Metricas que se quieren evaluar

    @abstractmethod
    def fit(self,x_train:np.ndarray,y_train:np.ndarray):
        """
        Ajusta modelo a datos de entrenamiento.
        Requiere ser implementado por subclases.
        Parametros:
        - x_train: array-like, Datos de entrada en cual se quieren realizar el entrenamiento del modelo.
        - y_train: array-like, Datos de entrada en cual se quieren realizar el entrenamiento del modelo.
        
        """
        pass

    @abstractmethod
    def train(self,x_train:np.ndarray,y_train:np.ndarray)->tuple[LossHistory,Figure]:
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
    def predict(self,x_test:np.ndarray )->np.ndarray:
        """
        Predicciones del modelo 
        Requiere ser implementado por subclases.

        Parametros:
        - x_test: array-like, Datos de entrada en cual se quieren realizar predicciones.

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

class HeuristicModel(ForecastModel):
    def fit(self, x_train: np.ndarray, y_train: np.ndarray):
        """ No se tiene método de ajuste para este modelo actualmente"""
        pass

    def train(self, x_train: np.ndarray, y_train: np.ndarray):
        """ No se tiene método de entrenamiento para este modelo actualmente"""
        history = LossHistory(train_loss=[], test_loss=[])
        fig = self.plot_loss(history)
        return history, fig
    
    def predict(self,x_test:np.ndarray,y_test:np.ndarray)->np.ndarray|None:
        """
        Predicciones del modelo.
        Toma los datos de ventas del mes y predice la venta mensual partiendo de las ventas a mitad del periodo
        """
        l = self.parameters['l']
        if len(y_test)==30:
            x = y_test[14]
            prediction = np.full(15, round(l*x, 0))
            return np.concatenate((y_test[:14],prediction))
        else: 
            print(f"Error: Datos no cumplen con longitud mínima. Esperado: 30 , Ingreso:{len(x_test)}")
            return None