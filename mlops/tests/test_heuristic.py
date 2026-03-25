import pytest
import datetime
import pandas as pd

from mlops.models import HeuristicModel

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
model = HeuristicModel(parameters={"l":8.4})

def test_sales_period():
    mask = dataset["productId"]=="product1"
    model.fit(dataset[mask])
    results = model.sales_period

    assert results[results["month"]==9]["monthly_sales"].iloc[0] == 14
    assert results[results["month"]==10]["monthly_sales"].iloc[0] == 1
    assert results[results["month"]==11]["monthly_sales"].iloc[0] == 4
    assert results[results["month"]==12]["monthly_sales"].iloc[0] == 10
    assert results[results["month"]==1]["monthly_sales"].iloc[0] == 2
    assert results[results["month"]==2]["monthly_sales"].iloc[0] == 1

    mask = dataset["productId"]=="product2"
    model.fit(dataset[mask])
    results = model.sales_period

    assert results[results["month"]==9]["monthly_sales"].iloc[0] == 37
    assert results[results["month"]==10]["monthly_sales"].iloc[0] == 49
    assert results[results["month"]==11]["monthly_sales"].iloc[0] == 29
    assert results[results["month"]==12]["monthly_sales"].iloc[0] == 37
    assert results[results["month"]==1]["monthly_sales"].iloc[0] == 38
    assert results[results["month"]==2]["monthly_sales"].iloc[0] == 9

def test_remaining_days():
    mask = dataset["productId"]=="product1"
    model.fit(dataset[mask])
    
    assert model.current_day==5
    assert model.current_month==2
    assert model.current_year==2025
    assert model.remaining_days==23

def test_get_sales_flow_index():
    mask = dataset["productId"]=="product1"
    model.fit(dataset[mask])
    assert model.sales_idx =="SBS" 

    mask = dataset["productId"]=="product2"
    model.fit(dataset[mask])
    assert model.sales_idx =="SSS" 

def test_get_client_sales():
    mask = dataset["productId"]=="product1"
    model.fit(dataset[mask])
    
    results = model.client_sales

    assert results[results["month"]==12]["client_sales"].iloc[0]==4
    assert results[results["month"]==1]["client_sales"].iloc[0]==2
    assert results[results["month"]==2]["client_sales"].iloc[0]==1

    mask = dataset["productId"]=="product2"
    model.fit(dataset[mask])
    
    results = model.client_sales

    assert results[results["month"]==12]["client_sales"].iloc[0]==18
    assert results[results["month"]==1]["client_sales"].iloc[0]==13
    assert results[results["month"]==2]["client_sales"].iloc[0]==4


