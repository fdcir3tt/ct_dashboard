import pytest
import pandas as pd
from matplotlib.figure import Figure
from graphs import stock_vs_sales  


# --- Datos de prueba ---
def sample_data():
    return pd.DataFrame({
        "fecha": pd.date_range("2024-01-01", periods=5, freq="D"),
        "productId": ["A", "A", "B", "A", "B"],
        "sales_day": [10, 20, 5, 15, 7],
        "stock": [100, 90, 80, 70, 60]
    })



# --- Test: dataset vacío ---
def get_text_from_fig(fig):
    """Devuelve todos los textos en la figura"""
    return [t.get_text() for t in fig.axes[0].texts]

def test_empty_dataset():
    df_empty = pd.DataFrame()
    fig = stock_vs_sales(df_empty, "A", "2024-01-01", "2024-01-05")
    assert isinstance(fig, Figure), "Debe retornar una figura aunque el dataset esté vacío"

def test_empty_dataset_text():
    df_empty = pd.DataFrame()
    fig = stock_vs_sales(df_empty, "A", "2024-01-01", "2024-01-05")
    texts = get_text_from_fig(fig)
    assert "No hay datos disponibles" in texts[0]

# --- Test: columnas faltantes ---
def test_missing_columns():
    df = pd.DataFrame({"foo": [1, 2], "bar": [3, 4]})
    fig = stock_vs_sales(df, "A", "2024-01-01", "2024-01-05")
    assert isinstance(fig, Figure), "Debe retornar una figura aunque falten columnas"

def test_missing_columns_text():
    df = pd.DataFrame({"foo": [1,2], "bar": [3,4]})
    fig = stock_vs_sales(df, "A", "2024-01-01", "2024-01-05")
    texts = get_text_from_fig(fig)
    assert "No se encuentran datos de fecha o del producto" in texts[0]

# --- Test: salida correcta ---
def test_returns_figure():
    df = sample_data()
    fig = stock_vs_sales(df, "A", "2024-01-01", "2024-01-05")
    assert isinstance(fig, Figure), "La función debe retornar un objeto matplotlib.figure.Figure"



