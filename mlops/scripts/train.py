import mlflow 
import pandas as pd 
import numpy as np
import inspect
import os

from typing import get_type_hints
from mlops.models import ForecastModel,Metrics,Figure
from mlops.utils import data_dir,get_experiment_config,ExperimentConfig,DatasetFilters,DatasetFilterConfig

def load_dataset(model_name:str,dataset:str,config:ExperimentConfig):
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
    dataset_config = DatasetFilterConfig(start_date= config.training_data_start_date,
                                         end_date= config.training_data_end_date,
                                         frequency= config.frequency,
                                         horizon= config.horizon,
                                         training_window=config.training_window)
    df = DatasetFilters(dataset_config).apply_period_filter(data)
    
    x_train,y_train,x_test,y_test = DatasetFilters(dataset_config).apply_split(data)
    return df,x_train,y_train,x_test,y_test



def load_model(model_name:str,config:ExperimentConfig)->ForecastModel:
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


def start_experiment(model_name:str,config:ExperimentConfig):
    """
    Comienza corrida de experimento

    Parametros:
    - model_name: str, Nombre del tipo de modelo siendo utilizado
    - config: ExperimentConfig , Configuración del experimento

    Regresa:
    - : None,
    """
    dataset = (config.dataset)
    frequency = (config.frequency)
    horizon = (config.horizon)
    training_window = (config.training_window)
    seed = (config.seed)
    feature_set = (config.feature_set)
    
    experiment_id = f"{dataset}_{frequency}_{horizon}"
    run_name = f"{model_name}_{feature_set}_{training_window}_{seed}"

    print(f"Experimento '{experiment_id}'")
    print(f"Empezando intento: {run_name}")

    mlflow.set_experiment(experiment_name=experiment_id)
    mlflow.start_run(run_name=run_name)


def logging(model_name:str,config:ExperimentConfig,metrics:Metrics,figures:dict[str,Figure]|None=None):
    """
    Realiza el logeo de parametros, métricas y visualizaciones resultado de
    la corrida del experimento.

    Parametros:
    - model_name: str, Nombre del tipo de modelo siendo utilizado
    - config: ExperimentConfig , Configuración del experimento
    - metrics: Metrics , Métricas resultado de corrida
    - figures: dict[str,matplotlib.Figure] , Visualizaciones resultado de corrida

    Regresa:
    - : None,
    """
    training_window = (config.training_window)
    seed = (config.seed)
    feature_set = (config.feature_set)

    # Parametros
    run_name = f"{model_name}_{feature_set}_{training_window}_{seed}"
    parameters = (config.parameters)

    
    mlflow.log_params(params=parameters)

    # Metricas
    for metric,value in metrics.__dict__.items():
       
        mlflow.log_metric(key=metric,value=value)
    
    # Visualizaciones
    if figures is not None:
        for fig_name,fig in figures.items():
            output_dir = r"./plots"
            os.makedirs(output_dir, exist_ok=True)  

            fig_path = os.path.join(output_dir, "test_plot.png")
            fig.savefig(fig_path)
            mlflow.log_artifact(fig_path)



def main():
    experiment_config = get_experiment_config()
    model_name = experiment_config.model_type
    dataset_name = experiment_config.dataset
    frequency = (experiment_config.frequency)
    horizon = (experiment_config.horizon)
    training_window = (experiment_config.training_window)
    seed = (experiment_config.seed)
    feature_set = (experiment_config.feature_set)

    dataset,x_train,y_train,x_test,y_test = load_dataset(model_name,dataset_name,experiment_config)
    model = load_model(model_name,experiment_config)

    
    experiment_id = f"{dataset_name.replace(" ","")}_{frequency}_{horizon}"
    run_name = f"{model_name}_{feature_set}_{training_window}_{seed}"
    
    print(f"Experimento '{experiment_id}'")
    print(f"Empezando intento: {run_name}")

    
    mlflow.set_experiment(experiment_name=experiment_id)
    with mlflow.start_run(run_name=run_name):

        if hasattr(model,"fit") and callable(getattr(model, "fit")):
            model.fit(dataset,experiment_config)
            
        train_results = model.train(x_train,y_train)
        test_fig,metrics = model.test(x_test,y_test)
        
        if train_results is None :
            figures={"test_plot":test_fig}
        else:
            loss_history,loss_fig = train_results 
            figures={"loss_plot":loss_fig,"test_plot":test_fig}
            
        logging(model_name,experiment_config,metrics,figures)


if __name__=="__main__":
    main()







