import numpy as np
import pandas as pd
import pytest

from mlops.utils import make_time_series,time_period,get_experiment_config,DatasetFilterConfig,DatasetFilters,Date,Path

def test_get_experiment_config():
    file_path = Path("test_config.yml")
    config = get_experiment_config(file_path)

    assert config.model_type=="arima"
    assert config.dataset=="HERMOSILLO, SON_MEMSTY050"
    assert config.metrics==["mae","mfe","mse","da"]
    assert config.parameters=={"p":20,"d":1,"q":4}
    assert config.training_data_start_date==Date(2025,1,1)
    assert config.training_data_end_date==Date(2026,3,15)


def test_make_time_series():

    period = time_period(Date(2000,1,1),Date(2000,4,1))
    df = pd.DataFrame(data=[[Date(2000,1,4),10],
                            [Date(2000,1,4),3], # día 4 del año
                            [Date(2000,2,20),42], # día 51 del año
                            [Date(2000,3,14),69], # día 74 del año
                            [Date(2000,3,21),1337]] , # día 81 del año
                      columns=["date","quantity"] )
    df["date"]=pd.to_datetime(df["date"])


    expected_series = np.array([0]*3+[13]+[0]*46+[42]+[0]*22+[69]+[0]*6+[1337]+[0]*11)
    expected_axis = pd.to_datetime(pd.Series(period)).to_numpy()

    # Días
    result = make_time_series(data=df,period=period)
    assert type(result)==type((np.array([]),np.array([])))
    assert all(result[0]==expected_axis)
    assert all(result[1]==expected_series)

    # Semanas
    # Meses


def test_DatasetFilterConfig():
    config = DatasetFilterConfig(start_date=Date(2000,1,1),
                                 end_date=Date(2000,4,1),
                                 frequency="daily",
                                 horizon=30,
                                 training_window=90)
    
    assert config.start_date == Date(2000,1,1)
    assert config.end_date == Date(2000,4,1)
    assert config.frequency == "daily"
    assert config.horizon == 30
    assert config.training_window == 90

    config = DatasetFilterConfig(start_date=Date(2000,1,1),
                                 end_date=Date(2000,4,1),
                                 frequency="daily",
                                 horizon=30,
                                 training_window=90)
    
def test_invalid_dates():
    with pytest.raises(ValueError):
        DatasetFilterConfig(
                start_date=Date(2025, 1, 10),
                end_date=Date(2025, 1, 1),
                frequency="daily",
                horizon=10,
                training_window=20,
            )
    
def test_invalid_horizon():
    with pytest.raises(ValueError):
        DatasetFilterConfig(
                start_date=Date(2025, 1, 1),
                end_date=Date(2025, 1, 10),
                frequency="daily",
                horizon=-10,
                training_window=20,
            )
        
def test_invalid_training_window():
    with pytest.raises(ValueError):
        DatasetFilterConfig(
                start_date=Date(2025, 1, 1),
                end_date=Date(2025, 1, 10),
                frequency="daily",
                horizon=10,
                training_window=-20,
            )
        
def test_DatasetFilters():
    df = pd.DataFrame(data=[[Date(2000,1,4),10],
                            [Date(2000,1,4),3], 
                            [Date(2000,2,20),42], # día 51 del año
                            [Date(2000,3,14),69], 
                            [Date(2000,3,21),1337],
                            [Date(2000,4,21),314],
                            [Date(2000,6,2),34],] , 
                      columns=["date","quantity"] )
    df["date"]=pd.to_datetime(df["date"])
    config = DatasetFilterConfig(start_date=Date(2000,1,1),
                                 end_date=Date(2000,4,14), # día 106
                                 frequency="daily",
                                 horizon=30,
                                 training_window=60)
    
    x_train,y_train,x_test,y_test = DatasetFilters(config).apply_split(df)

    assert type(x_train) == type(np.array([]))
    assert type(y_train) == type(np.array([]))
    assert type(x_test) == type(np.array([]))
    assert type(y_test) == type(np.array([]))

    assert x_train.shape == (60,),f"Unexpected shape: {x_train.shape}"
    assert y_train.shape == (60,),f"Unexpected shape: {x_train.shape}"
    assert x_test.shape == (30,),f"Unexpected shape: {x_train.shape}"
    assert y_test.shape == (30,),f"Unexpected shape: {x_train.shape}"

    assert y_train.sum() == 55, f"Unexpected y_train sum: {y_train.sum()}"
    assert x_train.max() == pd.Timestamp(Date(2000, 2, 29)), f"Unexpected x_train max: {x_train.max()}"

    assert y_test.sum() == 1406, f"Unexpected y_test sum: {y_test.sum()}"
    assert x_test.max() == pd.Timestamp(Date(2000, 3, 30)), f"Unexpected x_test max: {x_test.max()}"

