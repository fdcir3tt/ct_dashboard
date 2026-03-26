import numpy as np
import pandas as pd
import pytest

from mlops.utils import make_time_series,time_period,DatasetFilterConfig,DatasetFilters,Date

def test_make_time_series():

    period = time_period(Date(2000,1,1),Date(2000,4,1))
    df = pd.DataFrame(data=[[Date(2000,1,4),10],
                            [Date(2000,1,4),3], # 4
                            [Date(2000,2,20),42], # 51
                            [Date(2000,3,14),69], # 74
                            [Date(2000,3,21),1337]] , # 81
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
        
#def test_DatasetFilters():
