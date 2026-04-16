import pytest
import datetime
import pandas as pd
import numpy as np

from mlops.models import ForecastModel,HeuristicModel,Metrics
from mlops.utils import ExperimentConfig,calculate_metrics

# ==================================================================== #
#                       DATOS SINTÉTICOS
# ==================================================================== #

columns = ["productId","date","quantity","clientId"]

rows = [["product1",datetime.datetime(2025,2,5),1,"ACA0001"],
        ["product1",datetime.datetime(2025,1,2),2,"ACA0002"],
        ["product1",datetime.datetime(2024,12,1),2,"ACA0003"],
        ["product1",datetime.datetime(2024,12,1),1,"ACA0001"],
        ["product1",datetime.datetime(2024,12,4),1,"ACA0002"],
        ["product1",datetime.datetime(2024,12,3),6,"unknown"],
        ["product1",datetime.datetime(2024,11,3),1,"unknown"],
        ["product1",datetime.datetime(2024,11,3),2,"ACA0003"],
        ["product1",datetime.datetime(2024,11,3),1,"unknown"],
        ["product1",datetime.datetime(2024,10,2),1,"unknown"],
        ["product1",datetime.datetime(2024,9,1),14,"unknown"],

    ]+[ ["product2",datetime.datetime(2025,2,5),4,"ACA0002"],
        ["product2",datetime.datetime(2025,2,5),5,"unknown"],
        ["product2",datetime.datetime(2025,1,2),13,"ACA0001"],
        ["product2",datetime.datetime(2025,1,2),25,"unknown"],
        ["product2",datetime.datetime(2024,12,1),6,"ACA0003"],
        ["product2",datetime.datetime(2024,12,1),6,"ACA0001"],
        ["product2",datetime.datetime(2024,12,4),6,"ACA0002"],
        ["product2",datetime.datetime(2024,12,3),19,"unknown"],
        ["product2",datetime.datetime(2024,11,3),29,"unknown"],
        ["product2",datetime.datetime(2024,10,2),49,"unknown"],
        ["product2",datetime.datetime(2024,9,1),37,"unknown"],
        ]

dataset = pd.DataFrame(columns=columns,data=rows)
dataset["year"]= dataset["date"].dt.year
dataset["month"]= dataset["date"].dt.month

max_date = dataset["date"].max()
dataset["monthly_quantity"] = dataset.groupby(["year","month","productId"])["quantity"].transform("sum")




# ==================================================================== #
#                       MODELO ABSTRACTO FORECAST
# ==================================================================== #

def test_from_name():
    model= ForecastModel.from_name(model_name="Heuristic",
                                    parameters={"l":8.4})
    
    assert type(model) == type(HeuristicModel(parameters={'l':2}))

def test_calculate_metrics():
    y_pred = np.array([0,1,2,3,4,6,6,6,6,8])
    y_true = np.array([21,23,4,5,17,5,5,3,5,7])
    residuals = np.array([21,22,2,2,13,-1,-1,-3,-1,-1]) # y_true-y_pred

    expected_metrics = Metrics(mae= 6.70,
                               mfe= -5.30,
                               rmse= np.sqrt(111.50),
                               da= 5/9)
    
    result_metrics = calculate_metrics(y_pred,y_true)
    assert result_metrics.mae == expected_metrics.mae
    assert result_metrics.mfe == expected_metrics.mfe
    assert result_metrics.rmse == expected_metrics.rmse
    assert result_metrics.da == expected_metrics.da

# ==================================================================== #
#                       MODELO HEURISTICO
# ==================================================================== #


def test_sales_period():
    model = ForecastModel.from_name(model_name="Heuristic",
                                    parameters={"l":8.4})
    
    mask = dataset["productId"]=="product1"
    model.fit(dataset[mask])
    results = model.sales_period

    assert results[results["month"]==9]["monthly_quantity"].iloc[0] == 14
    assert results[results["month"]==10]["monthly_quantity"].iloc[0] == 1
    assert results[results["month"]==11]["monthly_quantity"].iloc[0] == 4
    assert results[results["month"]==12]["monthly_quantity"].iloc[0] == 10
    assert results[results["month"]==1]["monthly_quantity"].iloc[0] == 2
    assert results[results["month"]==2]["monthly_quantity"].iloc[0] == 1

    mask = dataset["productId"]=="product2"
    model.fit(dataset[mask])
    results = model.sales_period

    assert results[results["month"]==9]["monthly_quantity"].iloc[0] == 37
    assert results[results["month"]==10]["monthly_quantity"].iloc[0] == 49
    assert results[results["month"]==11]["monthly_quantity"].iloc[0] == 29
    assert results[results["month"]==12]["monthly_quantity"].iloc[0] == 37
    assert results[results["month"]==1]["monthly_quantity"].iloc[0] == 38
    assert results[results["month"]==2]["monthly_quantity"].iloc[0] == 9

def test_remaining_days():
    model = ForecastModel.from_name(model_name="Heuristic",
                                    parameters={"l":8.4})
    
    mask = dataset["productId"]=="product1"
    model.get_remaining_days(max_date)
    
    assert model.current_day==5
    assert model.current_month==2
    assert model.current_year==2025
    assert model.remaining_days==23

def test_get_sales_flow_index():
    model = ForecastModel.from_name(model_name="Heuristic",
                                    parameters={"l":8.4})
    mask = dataset["productId"]=="product1"
    model.get_sales_flow_index(dataset[mask])
    assert model.sales_idx =="SBS" 

    mask = dataset["productId"]=="product2"
    model.get_sales_flow_index(dataset[mask])
    assert model.sales_idx =="SSS" 

def test_get_client_sales():
    model = ForecastModel.from_name(model_name="Heuristic",
                                    parameters={"l":8.4})
    mask = dataset["productId"]=="product1"
    model.get_client_sales(dataset[mask])
    
    results = model.client_sales

    assert results[results["month"]==12]["client_sales"].iloc[0]==4
    assert results[results["month"]==1]["client_sales"].iloc[0]==2
    assert results[results["month"]==2]["client_sales"].iloc[0]==1

    mask = dataset["productId"]=="product2"
    model.get_client_sales(dataset[mask])
    
    results = model.client_sales

    assert results[results["month"]==12]["client_sales"].iloc[0]==18
    assert results[results["month"]==1]["client_sales"].iloc[0]==13
    assert results[results["month"]==2]["client_sales"].iloc[0]==4


def test_index_sum():
    model = ForecastModel.from_name(model_name="Heuristic",
                                    parameters={"l":8.4})
    mask = dataset["productId"]=="product1"
    model.fit(dataset[mask])
    
    assert model.s_n == [0.0, 0.0, 0.0, 8.0, 0.0]
    assert model.idx_sum == 8.0

    mask = dataset["productId"]=="product2"
    model.fit(dataset[mask])
    
    assert model.s_n == [0.0, 0.0, 0.0, 0.0, 38.0]
    assert model.idx_sum == 38.0


def test_predict_next_month_sale():
    model = ForecastModel.from_name(model_name="Heuristic",
                                    parameters={"l":8.4})
    mask = dataset["productId"]=="product1"
    model.fit(dataset[mask])
    result = model.predict_next_month_sale()

    assert result == 6

    mask = dataset["productId"]=="product2"
    model.fit(dataset[mask])
    result = model.predict_next_month_sale()

    assert result == 29

def test_missing_month_data():
    model= ForecastModel.from_name(model_name="Heuristic",
                                    parameters={"l":8.4})
    start_date = datetime.datetime(2024,9,1)
    end_date = datetime.datetime(2025,2,5)

    df = pd.DataFrame(data=[[start_date,"not_client",0],
                            [end_date,"not_client",0]],
                      columns=["date","clientId","quantity"])
    df["year"]= df["date"].dt.year
    df["month"]= df["date"].dt.month

    model.fit(df)
    prediction = model.predict_next_month_sale()
    assert prediction == 0

# ==================================================================== #
#                       MODELO ARIMA
# ==================================================================== #



def test_predict():
    model = ForecastModel.from_name(model_name="ARIMA",
                                    parameters={"p":1,"d":1,"q":2})

    mask = dataset["productId"]=="product1"
    model.fit(dataset[mask])

    # Predecir puntos ya conocidos
    dates = []
    current = datetime.datetime(2024,9,1)

    while current <= datetime.datetime(2024,12,9):
        dates.append(current)
        current += datetime.timedelta(days=1)

    x_input = np.array(dates)


    results = model.predict(x_input)
    expected_series = np.array([14]+[0]*30+[1]+[0]*31+[4]+[0]*27+[3]+[0]+[6,1]+[0]*5)
    

    assert type(results)==type(np.array([]))
    assert all(results==expected_series)

    # Predecir puntos desconocidos
    dates = []
    current = datetime.datetime(2024,9,1)

    while current <= datetime.datetime(2024,12,9):
        dates.append(current)
        current += datetime.timedelta(days=1)

    x_input = np.array(dates)
    config =   ExperimentConfig(
        dataset= "fake_name",
        parameters = {"p":1,
                      "d":0,
                      "q":0},
        training_data_start_date =current.date() ,
        training_data_end_date=datetime.datetime(2025,2,9).date(),
        model_type="ARIMA",
        horizon=30,
        frequency="daily",
        training_window=30,
        seed=42
        )
    
    model.fit(dataset,config)
    results = model.predict(x_input)

    assert type(results)==type(np.array([]))
    assert len(results)==len(x_input)
    assert len(model.known_data) == 30 # training_window
    assert type(model.confidence_int_lower_series)==type(pd.Series())
    assert type(model.confidence_int_upper_series)==type(pd.Series())

    
