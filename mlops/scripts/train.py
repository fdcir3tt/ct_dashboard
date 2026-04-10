import os
import mlflow 
import subprocess


from mlops.models import Metrics,Figure,ForecastModel,load_model
from mlops.utils import get_experiment_config,ExperimentConfig,load_dataset
from mlflow.data.pandas_dataset import PandasDataset

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


def logging(model_name:str,model:ForecastModel,config:ExperimentConfig,metrics:Metrics,figures:dict[str,Figure]|None=None):
    """
    Realiza el logeo de parametros, métricas y visualizaciones resultado de
    la corrida del experimento.

    Parametros:
    - model_name: str, Nombre del tipo de modelo siendo utilizado
    - model: ForecastModel, Modelo entrenado 
    - config: ExperimentConfig , Configuración del experimento
    - metrics: Metrics , Métricas resultado de corrida
    - figures: dict[str,matplotlib.Figure] , Visualizaciones resultado de corrida

    Regresa:
    - : None,
    """

    # Parametros
    start_date = config.training_data_start_date
    parameters = (config.parameters)

    dvc_rev = subprocess.check_output(["git", "rev-parse", "HEAD"]).strip().decode()

    mlflow.log_param("git_commit", dvc_rev)
    mlflow.log_params(params=parameters)
    mlflow.log_param(key="training_starting_date",value=start_date)

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

def log_model(model:ForecastModel,metrics:Metrics):
    if metrics.rmse > 5:
        return None
    
    if model.name == "ARIMA":
        mlflow.statsmodels.log_model(
                        statsmodels_model=model.model,
                        name="ARIMA", 
                        registered_model_name=model.name  
                    )


def main():
    experiment_config = get_experiment_config()
    model_name = experiment_config.model_type
    
    dataset_name = experiment_config.dataset
    frequency = (experiment_config.frequency)
    horizon = (experiment_config.horizon)
    training_window = (experiment_config.training_window)
    seed = (experiment_config.seed)
    feature_set = (experiment_config.feature_set)
    dataset,x_train,y_train,x_test,y_test = load_dataset(dataset_name,experiment_config)
    model = load_model(model_name,experiment_config)
    
    

    branch = dataset_name.split("_")[0]
    experiment_id = f"{branch}"
    run_name =f"{model_name}_{feature_set}_{seed}_<{frequency},{training_window},{horizon}>"
    
    print(f"Experimento '{experiment_id}'")
    print(f"Empezando intento: {run_name}")

    dataset_source_url = f"data/processed/{dataset_name}"
    mlflow_dataset: PandasDataset = mlflow.data.from_pandas(dataset, source=dataset_source_url,targets="quantity",name=dataset_name)

    mlflow.set_experiment(experiment_name=experiment_id)
    with mlflow.start_run(run_name=run_name,nested=True) as run:
        mlflow.log_input(mlflow_dataset, context="training")
        if hasattr(model,"fit") and callable(getattr(model, "fit")):
            model.fit(dataset,experiment_config)
                
        train_results = model.train(x_train,y_train)
        test_fig,metrics = model.test(x_test,y_test)
            
        if train_results is None :
            figures={"test_plot":test_fig}
        else:
            loss_history,loss_fig = train_results 
            figures={"loss_plot":loss_fig,"test_plot":test_fig}

        log_model(model,metrics)
               
        logging(model_name,model,experiment_config,metrics,figures)
        

if __name__=="__main__":
    main()







