import pytest
import pandas as pd
import numpy as np
from matplotlib.figure import Figure
from dashboard.graphs import *
from dashboard.data_loader import *
import matplotlib
matplotlib.use("Agg")

# -----------------------------------------------------------
# SETUP
# -----------------------------------------------------------

graphs = [period_sales,period_inventory,sales_hist,prepare_sales_heatmap_data]


# -----------------------------------------------
# BASE DE DATOS FALSA
# -----------------------------------------------

@pytest.fixture
def sample_sales_data():
    return pd.DataFrame({
        "date": pd.date_range("2023-01-01", periods=10, freq="D"),
        "productId": ["A", "A", "B", "B", "A", "B", "A", "B", "A", "B"],
        "category": ["X", "X", "Y", "Y", "X", "Y", "X", "Y", "X", "Y"],
        "state":["SONORA","SINALOA","MEXICO","SONORA","SINALOA","MEXICO","SONORA","SINALOA","MEXICO","ZACATECAS"],
        "sucursal":["HERMOSILLO, SON.","CULIACAN SIN.","TOLUCA ESTADO DE MEXICO","HERMOSILLO, SON.","CULIACAN SIN.","TOLUCA ESTADO DE MEXICO","HERMOSILLO, SON.","CULIACAN SIN.","TOLUCA ESTADO DE MEXICO","ZACATECAS"],
        "existence":[{'01A':20,'04A':25,'30A':25,'38A':25},{'01A':20,'04A':18,'30A':25,'38A':25},{'01A':25,'04A':25,'30A':22,'38A':25},{'01A':21,'04A':25,'30A':22,'38A':25},np.nan,{'01A':21,'04A':25,'30A':16,'38A':25},{'01A':16,'04A':18,'30A':25,'38A':25},np.nan,{'01A':16,'04A':18,'30A':15,'38A':25},{'01A':21,'04A':25,'30A':16,'38A':23}],
        "quantity": [5, 7, 3, 4, np.nan, 6, 8, np.nan, 10, 2],
        "sales_day": [5, 7, 3, 4, np.nan, 6, 8, np.nan, 10, 2],
        "month": [1]*10,
        "year": [2023]*10
    })

@pytest.fixture
def mexico_gdf():
    """ 
    Dataframe de información geográfica de méxico de prueba
    """
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
    monkeypatch.setattr("ct_sales_dashboard.graphs.load_mexico_shp", lambda: mexico_gdf)
    monkeypatch.setattr("streamlit_folium.st_folium", lambda *args, **kwargs: {})


# -----------------------------------------------------------
# PRUEBAS
# -----------------------------------------------------------


def test_empty_dataframe_returns_message_plot():
    """
    Prueba que verifica si gráficas manejan correctamente datasets vacíos
    """
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
    """
    Prueba que verifica si gráficas manejan correctamente datasets sin columna de fecha
    """
    df = pd.DataFrame({"productId": ["A"], "quantity": [10]})
    for g in graphs:
        if g==prepare_sales_heatmap_data:
            continue
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
    """
    Prueba que verifica si los filtros por fecha funcionan en cada gráfica
    """
    for g in graphs:
        if g==prepare_sales_heatmap_data:
             merged = g(
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
             assert merged["quantity"].sum() == 12
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
            assert plot_df["date"].min() >= pd.Timestamp("2023-01-03")
            assert plot_df["date"].max() <= pd.Timestamp("2023-01-05")

@pytest.mark.parametrize("column,values", [
    ("productId", ["A"]),
    ("category", ["X"]),
],)

def test_element_column_switching(sample_sales_data, column, values):
    """
    Prueba que verifica si las gráficas pueden cambiar entre producto y categoría sin problema.
    """
    for g in graphs:
        if g==prepare_sales_heatmap_data:
            plot_df = g(
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
            continue
        
        _, plot_df = g(
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
    """
    Prueba que verifica que no hayan valores faltantes 
    """
    for g in graphs:
        if g==prepare_sales_heatmap_data:
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
        if g==period_inventory:
            
            assert plot_df["stock"].isna().sum() == 0,"Despúes de la interpolación, no deben haber valores NaN"
            continue
    
        assert plot_df["sales_day"].isna().sum() == 0,"Despúes de la interpolación, no deben haber valores NaN"

def test_selected_element_without_data(sample_sales_data):
    """
    Prueba que verifica que gráficas manejen correctamente caso en donde se seleccione un elemento que no tenga datos
    """
    for g in graphs:
        if g==prepare_sales_heatmap_data:
            
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
    """
    Prueba que verifica que las gráficas adecuadas puedan manejar más de un elemento seleccionado
    """
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


def test_state_aggregation_correct(sample_sales_data):
    """
    Prueba que verifica si el mapa de color realiza sus cálculos correctamente
    """
    df = prepare_sales_heatmap_data(
        data=sample_sales_data,
        main_element="A",
        element_column="productId",
        start_date="2023-01-01",
        end_date="2023-01-10",
        val=True
    )

    sonora = df.loc[df["state"] == "SONORA", "quantity"].iloc[0]
    sinaloa = df.loc[df["state"] == "SINALOA", "quantity"].iloc[0]
    edomex = df.loc[df["state"] == "MEXICO", "quantity"].iloc[0]

    assert sonora == 13     # 5 + 8
    assert sinaloa == 7     # NaN ignorado
    assert edomex == 10

def test_states_with_no_sales_are_zero(sample_sales_data):
    """
    Prueba que verifica que el mapa de calor maneje correctamente estados en los cuales no hay ventas
    """
    df,_ =  prepare_sales_heatmap_data(
        data=sample_sales_data,
        main_element="A",
        element_column="productId",
        start_date="2023-01-01",
        end_date="2023-01-10",
        val=True
    )

    jalisco_sales = df.loc[
        df["state"] == "JALISCO", "quantity"
    ].iloc[0]

    assert jalisco_sales == 0

def test_category_switching(sample_sales_data):
    """
    Prueba que verifica si el mapa de calor pueda cambiar entre producto y categoría sin problema.
    """
    merged,_ =  prepare_sales_heatmap_data(
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
    assert merged["quantity"].sum() == 30

