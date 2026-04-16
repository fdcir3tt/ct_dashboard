import os
import copy
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import mlflow
import subprocess
import matplotlib
import warnings

from mlflow.pyfunc import PythonModel
from concurrent.futures import ProcessPoolExecutor, as_completed
from matplotlib.ticker import MultipleLocator,MaxNLocator
from matplotlib.figure import Figure
from mlops.utils import load_dataset,time_period,Date,ExperimentConfig,data_dir,Any,DEBUG,Path,calculate_metrics
from mlops.models import ForecastModel,HeuristicModel
from statsmodels.tools.sm_exceptions import ConvergenceWarning

DEBUG=True
if DEBUG:
    np.seterr(all='raise')
else:
    warnings.filterwarnings("ignore", category=ConvergenceWarning)
    warnings.filterwarnings(
    "ignore",
    message="Non-invertible starting MA parameters found.*"
)
matplotlib.use("Agg")
REGISTERED_MODEL_NAME = "arima_prototype"
MODEL_VERSION = 2
BRANCH = "HERMOSILLO, SON"
DATASETS_PATH = data_dir / 'processed' / BRANCH
EVAL_CONFIG = ExperimentConfig(
                                dataset = f"{BRANCH}_PAPXRX080", 
                                parameters ={"p":2,"d":1,"q":1},
                                training_data_start_date= Date(2025,1,1),
                                training_data_end_date= Date.today(),
                                model_type="ARIMA",
                                frequency="daily",   # daily, weekly, monthly
                                training_window=180, # 180 , 24 , 6
                                horizon=30,          # 30, 4, 1
                                seed=42,
                                metrics =['mae','rmse','mfe'])

def load_eval_models(config:ExperimentConfig)->tuple[HeuristicModel,PythonModel]:
    """
    Carga los modelos de pronóstico que se compararan. 
    
    Parametros:
    - model_type: str,  Tipo de modelo a cargar
    - model_parameters: dict[str,Any], Diccionario de parametros necesarios para cargar modelo

    Regresa:
    - base_model: HeuristicModel, Modelo de comparación
    - model: ForecastModel, Modelo a evaluar
    """
    base_model = ForecastModel.from_name(model_name="Heuristic",
                                        parameters={"l":8.4},
                                        test_metrics=config.metrics)
    if DEBUG:
        print(f"Modelo {base_model.name} cargado correctamente!")

    model = mlflow.pyfunc.load_model(f"models:/{REGISTERED_MODEL_NAME}/{MODEL_VERSION}")
    if DEBUG:
        print(f"Modelo de comparación cargado correctamente!")

    return base_model,model

def load_eval_period_data(config:ExperimentConfig)->tuple[list[tuple],Date,Date]:

    dataset = load_dataset(config.dataset,config,train_split=False)
    dataset = dataset.sort_values(by="date")
    
    if config.training_data_start_date == "oldest":
        min_date = dataset["date"].min()
    else:
        min_date = pd.to_datetime(config.training_data_start_date)

    if config.training_data_end_date == "latest":
        max_date = dataset["date"].max()
    else:
        max_date = pd.to_datetime(config.training_data_end_date)
    
    total_months =(max_date.year - min_date.year) * 12 + (max_date.month - min_date.month)
    number_of_periods = total_months - 6
    if DEBUG:
        print(f"Meses en total:{total_months}  Periodos de evaluación : {number_of_periods}")

    eval_periods = []
    current_date = min_date
    dummy_config = config.copy()
    for _ in range(number_of_periods):
        period = time_period (current_date.date(),(current_date+pd.DateOffset(months=7)).date())
        period = [pd.to_datetime(date) for date in period]
        
        dummy_config.training_data_start_date = period[0]
        dummy_config.training_data_end_date = period[-1]
        
        eval_periods.append(load_dataset(dummy_config.dataset,dummy_config))
        current_date += pd.DateOffset(months=1)
    return eval_periods,min_date.date(),max_date.date()



def calculate_eval_metrics(eval_periods:list[tuple],config:ExperimentConfig,base_model:HeuristicModel,model:PythonModel)->tuple[dict[str,Any],dict[str,Any]]:
    base_model_metrics = {}
    new_model_metrics = {}
    period = 1
    for period_data in eval_periods:
        df,x_train,y_train,x_test,y_test = period_data 
        start_date = pd.Timestamp(x_train.min()).date()
        end_date =pd.Timestamp(x_test.max()).date()

        months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
        if DEBUG:
            print(f"Periodo de evaluación: {start_date} - {end_date}")
    
        if df.empty:
            df = pd.DataFrame(data=[[start_date+pd.DateOffset(months=i),"not_client",0] for i  in range(months)],
                            columns=["date","clientId","quantity"])
            df["year"]= df["date"].dt.year
            df["month"]= df["date"].dt.month
        
        
        # Ajuste de periodo
        base_model.fit(df)

        # Valor real de ventas del siguiente mes
        if config.frequency=="daily" or config.frequency=="weekly":
            y_true = np.array( [y_test.sum()])
        if config.frequency=="monthly":
            y_true = y_test
        
        # Predicción del siguiente mes (base)
        base_pred = base_model.predict_next_month_sale()
        base_pred = np.array([base_pred])
        base_metrics = calculate_metrics(base_pred,y_true) 

        # Predicción del siguiente mes (modelo nuevo)
        if config.frequency=="daily" or config.frequency=="weekly":
            y_pred = model.predict(x_test).sum()
            y_pred = np.array([y_pred]).round()
        if config.frequency=="monthly":
            y_pred = model.predict(x_test)
        
        model_metrics = calculate_metrics(y_pred,y_true) 
        if DEBUG:
            print(f"Métricas de modelo Base: { base_metrics}")
            print(f"Métricas de modelo nuevo: {model_metrics}")

        key = f"period_{period}"
        base_model_metrics [key]={"y_pred":base_pred,
                                  "y_true":y_true,
                                  "metrics":base_metrics,
                                  "start_date":start_date,
                                  "end_date":end_date}
        
        new_model_metrics [key]={"y_pred":y_pred,
                                 "y_true":y_true,
                                 "metrics":model_metrics,
                                 "start_date":start_date,
                                 "end_date":end_date}
        period+=1
    return base_model_metrics,new_model_metrics


def plot_eval_graph(base_model_metrics:dict[str,Any],new_model_metrics:dict[str,Any],title:str,xlabel:str,ylabel:str)->Figure:

    
    base_model_predictions = []
    for period,data in base_model_metrics.items(): 
        base_model_predictions.append(data["y_pred"])

    new_model_predictions = []
    true_values = []
    for period,data in new_model_metrics.items(): 
        new_model_predictions.append(data["y_pred"])
        true_values.append(data["y_true"])


    

    fig, ax = plt.subplots(figsize=(10,5))
    ax.plot(true_values, label="Real", marker='o')
    ax.plot(base_model_predictions, label="Base", marker='o')
    ax.plot(new_model_predictions, label="ARIMA", marker='x')
    ax.set_ylim(0)
    ax.xaxis.set_major_locator(MultipleLocator(1)) 
    ax.yaxis.set_major_locator(MaxNLocator(integer=True)) 
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.legend()
    ax.grid(True)
    return fig

def metrics_table (metrics_results:dict[str,Any])->None:
    
    print("            RMSE  |  MAE  |  MFE")
    totals = {"rmse":0,"mae":0,"mfe":0}

    for period,results in metrics_results.items():
        metrics = results["metrics"]
        
        print(f"{period} : {metrics.rmse}{""}|{metrics.mae} | {metrics.mfe}")
        
        totals["rmse"]+=metrics.rmse
        totals["mae"]+=metrics.mae
        totals["mfe"]+=metrics.mfe
    
    print(f"Totales : {round(totals["rmse"])} | {round(totals["mae"])} |{round(totals["mfe"])}")

def new_model_wins_draws_losses(base_model_metrics:dict[str,Any],new_model_metrics:dict[str,Any])->tuple[int,int,int]:
    wins = 0
    draws = 0 
    losses = 0
    for period,data in base_model_metrics.items():
        base_metrics = data["metrics"]
        new_metrics = new_model_metrics[period]["metrics"]
        if new_metrics.rmse < base_metrics.rmse :
            wins +=1
        elif new_metrics.rmse == base_metrics.rmse:
            draws +=1
        else:
            losses+=1
    return wins,draws,losses  

def metric_analysis(global_results:dict[str,Any],model_name:str)->dict[str,Any]:
    
    distribution = {'rmse':[]}
    for productId,results in global_results.items():
        model_metrics = results[model_name]
        for period,data in model_metrics.items():
            metrics = data["metrics"] 
            distribution["rmse"].append(metrics.rmse)
        
    vector = np.array(distribution["rmse"])
    analytics = {f"{model_name}_RMSE_avg" : vector.mean(), 
                 f"{model_name}_RMSE_std" : vector.std(),
                 f"{model_name}_RMSE_min_value":vector.min(), 
                 f"{model_name}_RMSE_max_value":vector.max()}
    
    return analytics


def top_evaluations(global_results:dict[str,Any],model_name:str,best:bool=True)->list[Figure]:
    df_data = []
    for productId,results in global_results.items():
        model_metrics = results[model_name]
        distribution = {'rmse':[]}
        for period,data in model_metrics.items():
            metrics = data["metrics"] 
            distribution["rmse"].append(metrics.rmse)
        
        vector = np.array(distribution["rmse"])
        analytics = {"productId":productId,"RMSE_avg" : vector.mean()}
        df_data.append(analytics)
    df = pd.DataFrame(data=df_data)
    df = df.sort_values("RMSE_avg",ascending=best)
    top_products = df['productId'][:5]

    figures = []
    for productId in top_products:
        figures.append(global_results[productId]["prediction_plot"])
        
    return figures
     
def main(dataset_name:str,config:ExperimentConfig)->dict[str,Any]:
    model_name = config.model_type
    base_model,model = load_eval_models(config)
    eval_periods,current_date,max_date = load_eval_period_data(config)

    base_model_metrics,new_model_metrics = calculate_eval_metrics(eval_periods=eval_periods,
                                                                  config=config,
                                                                  base_model=base_model,
                                                                  model=model)
    if DEBUG:
        print(f"Base")
        metrics_table(base_model_metrics)     
    
        print(f"\n{model_name}")
        metrics_table(new_model_metrics) 


    branch,productId = dataset_name.split("_",1)
    title=f"Predicción de Ventas Mensuales\nSucursal:{branch}  Producto:{productId}\nPeriodo:{current_date} / {max_date}"
    xlabel= "Periodo(meses)"
    ylabel= "Ventas (unidades de producto)"
    fig = plot_eval_graph(base_model_metrics=base_model_metrics,
                          new_model_metrics=new_model_metrics,
                          title=title,
                          xlabel=xlabel,
                          ylabel=ylabel)
    return {"productId":productId,"HeuristicModel":base_model_metrics,f"{model_name}":new_model_metrics,"prediction_plot":fig}
    
def evaluate_with_product(productId:str):
    dataset_name = f"{BRANCH}_{productId}"
    local_config = copy.deepcopy(EVAL_CONFIG)
    local_config.dataset = dataset_name
    results = main(dataset_name, local_config)
    if DEBUG:
        print(f"\nComenzando comparación de modelos con producto: {productId}...\n")
    # Victorias de periodo
    wins,draws,losses = new_model_wins_draws_losses(results["HeuristicModel"],results[local_config.model_type])

    return productId,results,(wins,draws,losses)


if __name__=="__main__":
    model_name=EVAL_CONFIG.model_type
    mlflow.set_experiment(experiment_name=BRANCH)
    win_counter = {"wins":0,"draws":0,"losses":0}
    branch_products = [ p.split('.')[0] for p in os.listdir(DATASETS_PATH)]
    global_results = {}

    with mlflow.start_run(run_name=f"{model_name}_vs_HeuristicModel",nested=True) as run:

        with ProcessPoolExecutor(max_workers=4) as executor:
            branch_products = branch_products[4050:4100]
            futures = [executor.submit(evaluate_with_product, productId) for productId in branch_products]
            counter = 0
            total_products = len(branch_products)
            for f in as_completed(futures):
                productId, results, (wins, draws, losses) = f.result()

                # Actualización 
                global_results[productId] = results
                win_counter["wins"]+=wins
                win_counter["draws"]+=draws
                win_counter["losses"]+=losses
                print(f"Productos evaluados:{counter} / {total_products}",end='\r')
                counter +=1

        # Analisis de métricas
        model_analysis = metric_analysis(global_results,model_name)
        base_analysis = metric_analysis(global_results,"HeuristicModel")

        # Mejores y peores evaluaciones

        best_figures = top_evaluations(global_results,model_name)
        worst_figures = top_evaluations(global_results,model_name,best=False)

        # Logging
        dvc_rev = subprocess.check_output(["git", "rev-parse", "HEAD"]).strip().decode()

        mlflow.log_param("git_commit", dvc_rev)
        mlflow.log_metrics(win_counter)
        mlflow.log_metrics(base_analysis)
        mlflow.log_metrics(model_analysis)
        

        i = 1
        for fig in best_figures:
            output_dir = r"./plots"
            os.makedirs(output_dir, exist_ok=True)  

            fig_path = os.path.join(output_dir, f"top_{i}_eval_plot.png")
            fig.savefig(fig_path)
            mlflow.log_artifact(fig_path)
            i+=1

        i = 1
        for fig in worst_figures:
            output_dir = r"./plots"
            os.makedirs(output_dir, exist_ok=True)  

            fig_path = os.path.join(output_dir, f"bottom_{i}_eval_plot.png")
            fig.savefig(fig_path)
            mlflow.log_artifact(fig_path)
            i+=1