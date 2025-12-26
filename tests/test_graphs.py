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

graphs = [period_sales,sales_velocity,sales_hist,interactive_sales_heat_map]#abc_bar_chart]

# -----------------------------------------------
# BASE DE DATOS FALSA
# -----------------------------------------------

@pytest.fixture
def sample_sales_data():
    return pd.DataFrame({
        "fecha": pd.date_range("2023-01-01", periods=10, freq="D"),
        "productId": ["A", "A", "B", "B", "A", "B", "A", "B", "A", "B"],
        "category": ["X", "X", "Y", "Y", "X", "Y", "X", "Y", "X", "Y"],
        "state":["SONORA","SINALOA","MEXICO","SONORA","SINALOA","MEXICO","SONORA","SINALOA","MEXICO","ZACATECAS"],
        "sucursal":["HERMOSILLO, SON.","CULIACAN SIN.","TOLUCA ESTADO DE MEXICO","HERMOSILLO, SON.","CULIACAN SIN.","TOLUCA ESTADO DE MEXICO","HERMOSILLO, SON.","CULIACAN SIN.","TOLUCA ESTADO DE MEXICO","ZACATECAS"],
        "cantidad": [5, 7, 3, 4, np.nan, 6, 8, np.nan, 10, 2],
        "sales_day": [5, 7, 3, 4, np.nan, 6, 8, np.nan, 10, 2],
        "month": [1]*10,
        "year": [2023]*10
    })

@pytest.fixture
def mexico_gdf():
    return pd.DataFrame({
        "state": [
            "SONORA", "SINALOA", "MEXICO",
            "ZACATECAS", "JALISCO"
        ],
        "NAME_1": [
            "Sonora", "Sinaloa", "Estado de México",
            "Zacatecas", "Jalisco"
        ],
        "geometry": [None]*5
    })

@pytest.fixture(autouse=True)
def mock_external_dependencies(monkeypatch, mexico_gdf):
    monkeypatch.setattr("graphs.load_mexico_shp", lambda: mexico_gdf)
    monkeypatch.setattr("streamlit_folium.st_folium", lambda *args, **kwargs: {})


# -----------------------------------------------------------
# PRUEBAS
# -----------------------------------------------------------


def test_empty_dataframe_returns_message_plot():
    df = pd.DataFrame()
    for g in graphs:
        fig = g(
            data=df,
            main_element="A",
            selected_elements=["A"],
            element_column="productId",
            branch="HERMOSILLO, SON.",
            start_date="2023-01-01",
            end_date="2023-01-10"
        )

        assert isinstance(fig, matplotlib.figure.Figure)

def test_missing_date_column():
    df = pd.DataFrame({"productId": ["A"], "cantidad": [10]})
    for g in graphs:
        fig = g(
            data=df,
            main_element = "A",
            selected_elements=["A"],
            element_column="productId",
            branch="HERMOSILLO, SON.",
            start_date="2023-01-01",
            end_date="2023-01-10"
        )
    
        assert isinstance(fig, matplotlib.figure.Figure)

def test_date_filtering(sample_sales_data):
    for g in graphs:
        if g==interactive_sales_heat_map:
             _, merged = g(
                data=sample_sales_data,
                main_element="A",
                element_column="productId",
                start_date="2023-01-01",
                end_date="2023-01-04",
                val=True
            )

            # Solo A en primeros cuatro días:
            # 2023-01-01 (SONORA) → 5
            # 2023-01-02 (SINALOA) → 7
            # 2023-01-03 (B) → ignorado
            # 2023-01-04 (B) → ignorado
             assert merged["cantidad"].sum() == 12
             continue
        
        _,plot_df = g(
            data=sample_sales_data,
            main_element="A",
            selected_elements=["A"],
            element_column="productId",
            branch="HERMOSILLO, SON.",
            start_date="2023-01-03",
            end_date="2023-01-05",
            val=True
        )

        if plot_df.empty:
            assert plot_df.empty
        else:
            assert plot_df["fecha"].min() >= pd.Timestamp("2023-01-03")
            assert plot_df["fecha"].max() <= pd.Timestamp("2023-01-05")

@pytest.mark.parametrize("column,values", [
    ("productId", ["A"]),
    ("category", ["X"]),
],)

def test_element_column_switching(sample_sales_data, column, values):
    for g in graphs:
        fig, plot_df = g(
            data=sample_sales_data,
            main_element = values[0],
            selected_elements=values,
            element_column=column,
            branch = "HERMOSILLO, SON.",
            start_date="2023-01-01",
            end_date="2023-01-10",
            val=True
        )

        assert plot_df[column].isin(values).all()

def test_missing_quantity_interpolation(sample_sales_data):
    for g in graphs:
        if g in [interactive_sales_heat_map]:
            continue
        if g==sales_velocity:
            fig, plot_df = g(
            data=sample_sales_data,
            selected_elements=["A"],
            element_column="productId",
            branch = "HERMOSILLO, SON.",
            start_date="2023-01-01",
            end_date="2023-01-10",
            val=True
        )

    
            assert plot_df["sales_velocity"].isna().sum() == 0,"Despúes de la interpolación, no deben haber valores NaN"
            continue

        _, plot_df = g(
            data=sample_sales_data,
            main_element="A",
            selected_elements=["A"],
            element_column="productId",
            branch = "HERMOSILLO, SON.",
            start_date="2023-01-01",
            end_date="2023-01-10",
            val=True
        )

    
        assert plot_df["sales_day"].isna().sum() == 0,"Despúes de la interpolación, no deben haber valores NaN"


def test_selected_element_without_data(sample_sales_data):
    for g in graphs:
        if g==interactive_sales_heat_map:
            fig,_= g(
                data=sample_sales_data,
                main_element ="C", # No existe
                selected_elements=["C"],  # No existe
                element_column="productId",
                start_date="2023-01-01",
                end_date="2023-01-10"
            )
            assert isinstance(fig, matplotlib.figure.Figure)
            continue

        fig = g(
            data=sample_sales_data,
            main_element ="C", # No existe
            selected_elements=["C"],  # No existe
            element_column="productId",
            branch = "HERMOSILLO, SON.",
            start_date="2023-01-01",
            end_date="2023-01-10"
        )

        assert isinstance(fig, matplotlib.figure.Figure)

def test_multiple_products_plot(sample_sales_data):
    for g in [period_sales,sales_velocity]:
        fig = g(
            data=sample_sales_data,
            selected_elements=["A", "B"],
            element_column="productId",
            branch="HERMOSILLO, SON.",
            start_date="2023-01-01",
            end_date="2023-01-10"
        )

        ax = fig.axes[0]
        
        assert len(ax.lines) >= 2,"Se esperan al menos dos curvas y rectas de tendencia"

def test_missing_required_columns():
    df = pd.DataFrame({"productId": ["A"], "cantidad": [5]})

    fig = interactive_sales_heat_map(
        data=df,
        main_element="A",
        element_column="productId",
        start_date="2023-01-01",
        end_date="2023-01-10"
    )

    assert fig is not None

def test_state_aggregation_correct(sample_sales_data):
    _, merged = interactive_sales_heat_map(
        data=sample_sales_data,
        main_element="A",
        element_column="productId",
        start_date="2023-01-01",
        end_date="2023-01-10",
        val=True
    )

    sonora = merged.loc[merged["state"] == "SONORA", "cantidad"].iloc[0]
    sinaloa = merged.loc[merged["state"] == "SINALOA", "cantidad"].iloc[0]
    edomex = merged.loc[merged["state"] == "MEXICO", "cantidad"].iloc[0]

    assert sonora == 13     # 5 + 8
    assert sinaloa == 7     # NaN ignorado
    assert edomex == 10

def test_states_with_no_sales_are_zero(sample_sales_data):
    _, merged = interactive_sales_heat_map(
        data=sample_sales_data,
        main_element="A",
        element_column="productId",
        start_date="2023-01-01",
        end_date="2023-01-10",
        val=True
    )

    jalisco_sales = merged.loc[
        merged["state"] == "JALISCO", "cantidad"
    ].iloc[0]

    assert jalisco_sales == 0


    

def test_category_switching(sample_sales_data):
    _, merged = interactive_sales_heat_map(
        data=sample_sales_data,
        main_element="X",
        element_column="category",
        start_date="2023-01-01",
        end_date="2023-01-10",
        val=True
    )

    # X aparece en:
    # SONORA: 5 + 8 = 13
    # SINALOA: 7
    # MÉXICO: 10
    assert merged["cantidad"].sum() == 30

def test_val_true_adds_element_column(sample_sales_data):
    _, merged = interactive_sales_heat_map(
        data=sample_sales_data,
        main_element="A",
        element_column="productId",
        start_date="2023-01-01",
        end_date="2023-01-10",
        val=True
    )

    assert "productId" in merged.columns
    assert (merged["productId"] == "A").all()
