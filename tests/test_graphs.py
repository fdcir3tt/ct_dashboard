import pytest
import pandas as pd
import numpy as np
from matplotlib.figure import Figure
from graphs import *
import matplotlib
matplotlib.use("Agg")

# -----------------------------------------------------------
# SETUP
# -----------------------------------------------------------

graphs = [period_sales,sales_velocity,sales_hist,interactive_sales_heat_map,abc_bar_chart]

# -----------------------------------------------
# BASE DE DATOS FALSA
# -----------------------------------------------

@pytest.fixture
def sample_sales_data():
    return pd.DataFrame({
        "fecha": pd.date_range("2023-01-01", periods=10, freq="D"),
        "productId": ["A", "A", "B", "B", "A", "B", "A", "B", "A", "B"],
        "category": ["X", "X", "Y", "Y", "X", "Y", "X", "Y", "X", "Y"],
        "cantidad": [5, 7, 3, 4, np.nan, 6, 8, np.nan, 10, 2],
        "month": [1]*10,
        "year": [2023]*10
    })

# -----------------------------------------------------------
# PRUEBAS
# -----------------------------------------------------------


def test_empty_dataframe_returns_message_plot():
    df = pd.DataFrame()

    fig = period_sales(
        data=df,
        selected_elements=["A"],
        element_column="productId",
        start_date="2023-01-01",
        end_date="2023-01-10"
    )

    assert isinstance(fig, matplotlib.figure.Figure)

def test_missing_fecha_column():
    df = pd.DataFrame({"productId": ["A"], "cantidad": [10]})

    fig = period_sales(
        data=df,
        selected_elements=["A"],
        element_column="productId",
        start_date="2023-01-01",
        end_date="2023-01-10"
    )
    
    assert isinstance(fig, matplotlib.figure.Figure)

def test_date_filtering(sample_sales_data):
    fig, plot_df = period_sales(
        data=sample_sales_data,
        selected_elements=["A"],
        element_column="productId",
        start_date="2023-01-03",
        end_date="2023-01-05",
        val=True
    )

    assert plot_df["fecha"].min() >= pd.Timestamp("2023-01-03")
    assert plot_df["fecha"].max() <= pd.Timestamp("2023-01-05")

@pytest.mark.parametrize("column,values", [
    ("productId", ["A"]),
    ("category", ["X"]),
])
def test_element_column_switching(sample_sales_data, column, values):
    fig, plot_df = period_sales(
        data=sample_sales_data,
        selected_elements=values,
        element_column=column,
        start_date="2023-01-01",
        end_date="2023-01-10",
        val=True
    )

    assert plot_df[column].isin(values).all()

def test_missing_quantity_interpolation(sample_sales_data):
    fig, plot_df = period_sales(
        data=sample_sales_data,
        selected_elements=["A"],
        element_column="productId",
        start_date="2023-01-01",
        end_date="2023-01-10",
        val=True
    )

    
    assert plot_df["sales_day"].isna().sum() == 0,"Despúes de la interpolación, no deben haber valores NaN"


def test_selected_element_without_data(sample_sales_data):
    fig = period_sales(
        data=sample_sales_data,
        selected_elements=["C"],  #No existe
        element_column="productId",
        start_date="2023-01-01",
        end_date="2023-01-10"
    )

    assert isinstance(fig, matplotlib.figure.Figure)

def test_multiple_products_plot(sample_sales_data):
    fig = period_sales(
        data=sample_sales_data,
        selected_elements=["A", "B"],
        element_column="productId",
        start_date="2023-01-01",
        end_date="2023-01-10"
    )

    ax = fig.axes[0]
    
    assert len(ax.lines) >= 2,"Se esperan al menos dos curvas y rectas de tendencia"
