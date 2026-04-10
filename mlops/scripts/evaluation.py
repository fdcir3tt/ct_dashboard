import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from typing import Any
from matplotlib.figure import Figure
from mlops.utils import load_dataset,time_period,Date
from mlops.models import ForecastModel,HeuristicModel

# Configuración
MODEL_TYPE = "ARIMA"
MODEL_PARAMS= {"p":20,"d":1,"q":4}
DATASET_NAME = "HERMOSILLO, SON_MEMSTY050" # MEMSTY050 ,CARHPP4170 ,CAMDAH5500 , NBKAPC1690, PAPXRX080,GABACT340


EVAL_CONFIG = { "training_data_start_date":"oldest",
              "training_data_end_date":"latest",
              "frequency":"daily", # fijo
              "horizon":30, #fijo
              "training_window":180} #fijo


def load_eval_models(model_type:str,model_parameters:dict[str,Any])->tuple[HeuristicModel,ForecastModel]:
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
                                        test_metrics=['mae','rmse','mfe'])
    
    print(f"Modelo {base_model.type} cargado correctamente!")

    model = ForecastModel.from_name(model_name=model_type,
                                    parameters=model_parameters,
                                    test_metrics=['mae','rmse','mfe'])
    print(f"Modelo {model.type} cargado correctamente!")

    return base_model,model

def load_eval_period_data(dataset_name:str,config:dict[str,Any])->tuple[list[tuple],Date,Date]:

    dataset = load_dataset(dataset_name,config,train_split=False)
    dataset = dataset.sort_values(by="date")
    

    current_date = dataset["date"].min()
    max_date = dataset["date"].max()
    
    total_months =(max_date.year - current_date.year) * 12 + (max_date.month - current_date.month)
    number_of_periods = total_months - 6
    eval_periods = []
    print(f"Meses en total:{total_months}  Periodos : {number_of_periods}")

    for _ in range(number_of_periods):
        period = time_period (current_date.date(),(current_date+pd.DateOffset(months=7)).date())
        period = [pd.to_datetime(date) for date in period]
        
        config["training_data_start_date"] = period[0]
        config["training_data_end_date"] = period[-1]
        
        eval_periods.append(load_dataset(dataset_name,config))
        current_date += pd.DateOffset(months=1)
    return eval_periods,current_date.date(),max_date.date()



def calculate_eval_metrics(eval_periods:list[tuple],config:dict[str,Any],base_model:HeuristicModel,model:ForecastModel)->tuple[dict[str,Any],dict[str,Any]]:
    base_model_metrics = {}
    new_model_metrics = {}
    period = 1
    for period_data in eval_periods:
        df,x_train,y_train,x_test,y_test = period_data 
        start_date = pd.Timestamp(x_train.min()).date()
        end_date =pd.Timestamp(x_test.max()).date()

        months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)

        print(f"Periodo de evaluación: {start_date} - {end_date}")
    
        if df.empty:
            df = pd.DataFrame(data=[[start_date+pd.DateOffset(months=i),"not_client",0] for i  in range(months)],
                            columns=["date","clientId","quantity"])
            df["year"]= df["date"].dt.year
            df["month"]= df["date"].dt.month
        
        
        # Ajuste de periodo
        base_model.fit(df)
        if hasattr(model,"fit") and callable(getattr(model, "fit")):
            model.fit(df)

        # Valor real de ventas del siguiente mes
        if config["frequency"]=="daily" or config["frequency"]=="weekly":
            y_true = np.array( [y_test.sum()])
        if config["frequency"]=="monthly":
            y_true = y_test
        
        # Predicción del siguiente mes (base)
        base_pred = base_model.predict_next_month_sale()
        base_pred = np.array([base_pred])
        base_metrics = base_model.calculate_metrics(base_pred,y_true) 

        # Predicción del siguiente mes (modelo nuevo)
        if EVAL_CONFIG["frequency"]=="daily" or EVAL_CONFIG["frequency"]=="weekly":
            y_pred = model.predict(x_test).sum()
            y_pred = np.array([y_pred])
        if EVAL_CONFIG["frequency"]=="monthly":
            y_pred = model.predict(x_test)
        
        model_metrics = model.calculate_metrics(y_pred,y_true) 

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
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.legend()
    ax.grid(True)
    return fig




def main():
    base_model,model = load_eval_models(MODEL_TYPE,MODEL_PARAMS)
    eval_periods,current_date,max_date = load_eval_period_data(DATASET_NAME,EVAL_CONFIG)

    base_model_metrics,new_model_metrics = calculate_eval_metrics(eval_periods=eval_periods,
                                                                  config=EVAL_CONFIG,
                                                                  base_model=base_model,
                                                                  model=model)
    branch,productId = DATASET_NAME.split("_",1)
    title=f"Predicción de Ventas Mensuales\nSucursal:{branch}  Producto:{productId}\nPeriodo:{current_date} / {max_date}"
    xlabel= "Periodo(meses)"
    ylabel= "Ventas (unidades de producto)"
    fig = plot_eval_graph(base_model_metrics=base_model_metrics,
                          new_model_metrics=new_model_metrics,
                          title=title,
                          xlabel=xlabel,
                          ylabel=ylabel)
    plt.show()

if __name__=="__main__":
    main()
