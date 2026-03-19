import os
import yaml
import mlflow 
import pandas as pd 
import numpy as np

from mlops.models import ForecastModel,Any,Metrics,Figure
from mlops.utils import data_dir,get_experiment_config,Path,ExperimentConfig,DatasetFilters,DatasetFilterConfig

def load_dataset(model_name:str,dataset:str,config:ExperimentConfig):
    """
    Carga datos que se utilizaran para el experimento de entrenamiento de un modelo

    Parametros:
    - model_name: str, Nombre del tipo de modelo siendo utilizado
    - dataset: str, Nombre de los datos que se quieren utilizar
    - config: ExperimentConfig, Configuración del experimento

    Regresa:
    - x_train: numpy.ndarray, Datos de entrada de entrenamiento
    - y_train: numpy.ndarray, Datos de objetivo de entrenamiento
    - x_test: numpy.ndarray, Datos de entrada de prueba
    - y_test: numpy.ndarray, Datos de objetivo de prueba
    """
    branch, productId = dataset.split('_', 1)
    file_path = data_dir/'processed'/ branch / f'{productId}.parquet'
    
    data = pd.read_parquet(file_path)
    dataset_config = DatasetFilterConfig(start_date=(config.get("training_data_start_dates")).get(model_name),
                                         end_date=(config.get("training_data_end_dates")).get(model_name),
                                         frequency=(config.get("frequencies")).get(model_name),
                                         horizon=(config.get("horizons")).get(model_name),
                                         training_window=(config.get("training_windows")).get(model_name))
    
    x_train,y_train,x_test,y_test = DatasetFilters(dataset_config).apply_split(data)
    return x_train,y_train,x_test,y_test



def load_model(model_name:str,config:ExperimentConfig)->ForecastModel:
    """
    Carga el modelo específicado

    Parametros:
    - model_name: str, Nombre del tipo de modelo siendo utilizado
    - config: ExperimentConfig , Configuración del experimento
    
    Regresa:
    - model: ForecastModel, Modelo de regresión temporal
    """
    parameters = (config.get("parameters")).get(model_name)
    model = ForecastModel.from_name(model_name=model_name,
                                    parameters=parameters)
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
    dataset = (config.get("datasets")).get(model_name)
    frequency = (config.get("frequencies")).get(model_name)
    horizon = (config.get("horizons")).get(model_name)
    training_window = (config.get("training_windows")).get(model_name)
    seed = (config.get("seeds")).get(model_name)
    feature_set = (config.get("feature_set")).get(model_name)
    
    experiment_id = f"{dataset}_{frequency}_{horizon}"
    run_id = f"{model_name}_{feature_set}_{training_window}_{seed}"

    mlflow.set_experiment(experiment_name=experiment_id)
    mlflow.start_run(run_name=run_id)


def logging(model_name:str,config:ExperimentConfig,metrics:Metrics,figures:dict[str,Figure]):
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
    training_window = (config.get("training_windows")).get(model_name)
    seed = (config.get("seeds")).get(model_name)
    feature_set = (config.get("feature_set")).get(model_name)

    # Parametros
    run_id = f"{model_name}_{feature_set}_{training_window}_{seed}"
    parameters = (config.get("parameters")).get(model_name)
    mlflow.log_params(run_id=run_id,params=parameters)

    # Metricas
    for metric,value in metrics.items():
        mlflow.log_metric(key=metric,value=value)
    
    # Visualizaciones
    for fig_name,fig in figures.items():
        fig_path = f"/tmp/{fig_name}.png"
        fig.savefig(fig_path)
        mlflow.log_artifact(fig_path)



def main():
    experiment_config = get_experiment_config()
    model_types = experiment_config.get("model_types")
    for model_name in model_types:
        dataset = (experiment_config.get("datasets")).get(model_name)
        x_train,y_train,x_test,y_test = load_dataset(model_name,dataset,experiment_config)
        
        model = load_model(model_name,experiment_config)
        
        start_experiment(model_name,experiment_config)
        
        loss_history,loss_fig = model.train(x_train,y_train)
        test_fig,metrics = model.test(x_test,y_test)

        figures={"loss_plot":loss_fig,"test_plot":test_fig}
        logging(model_name,experiment_config,metrics,figures)

if __name__=="__main__":
    main()







