import streamlit as st
import pandas as pd
import numpy as np
import datetime
import os
import src.graphs as gr  
from src.preprocess import process_data

# -----------------------------------------------------------
# CONFIGURACIÓN INICIAL
# -----------------------------------------------------------
st.set_page_config(page_title="Inventario CT International", layout="wide")

st.markdown("""
    <style>
        .main-header {
            font-size: 28px;
            font-weight: bold;
            color: #ffffff;
            background-color: #C81E2B;
            padding: 10px 20px;
            border-radius: 5px;
        }
        .metric-card {
            text-align: center;
            background-color: #f8f9fa;
            color: #333333;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">📦 Inventario CT International</div>', unsafe_allow_html=True)

# -----------------------------------------------------------
# FILTROS
# -----------------------------------------------------------
st.sidebar.header("Filtros")
producto = st.sidebar.selectbox("Producto", ['MEMDAT6830',
 'SUBCCT010',
 'DDUACR220',
 'ACCPCM1160',
 'CJNNTE010',
 'IMPECL320',
 'CABITL4210',
 'VENBLR170',
 'DDUACR020',
 'IMPSTR1020',
 'CARGO100',
 'CABITL265',
 'VENBLR270',
 'DDUDAT520',
 'MEMDAT6260',
 'VENNCB090',
 'ACCDAT1460',
 'DDUDAT450',
 'KITTPL360',
 'NBKVIC690',
 'NBKCDP1670',
 'ESDKPK1820',
 'GABBLR320',
 'MOULEN060',
 'ACCTRG3480'])
fecha_inicio = st.sidebar.date_input("Inicio", datetime.date(2025, 10, 1))
fecha_fin = st.sidebar.date_input("Fin", datetime.date(2025, 11, 1))

# -----------------------------------------------------------
# CARGA DE DATOS
# -----------------------------------------------------------

data = process_data ()
categorias = pd.read_csv("data/categorias.csv")
categorias = list(categorias["nombre"])


# Crear carpeta de salida si no existe
os.makedirs("plots", exist_ok=True)

# -----------------------------------------------------------
# LLAMADA A LAS FUNCIONES DE TU MÓDULO
# -----------------------------------------------------------
gr.stock_v_sales(data,producto)
gr.sales_hist(data["sales_day"])
gr.sales_heat_map(data,producto)
gr.profits_sales_bar(data, categorias[20:25])

# -----------------------------------------------------------
# VISUALIZACIÓN EN STREAMLIT
# -----------------------------------------------------------
st.image("plots/almacen_ventas.png", caption="Stock y Ventas - 2025", use_container_width=True)

# Info del producto
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(f"**Código:** {producto}")
    st.markdown("**Producto Sustituto:** <Código ejemplo>")
with col2:
    st.markdown("**Productos Acompañados:** <Código ejemplo>, <Código ejemplo>")
    st.markdown("**Día más vendido:** día ")
with col3:
    st.markdown("**Clientes frecuentes:** <Código ejemplo>, <Código ejemplo>")

# Histograma y mapa
col1, col2 = st.columns(2)
with col1:
    st.image("plots/hist_ventas_prod.png", caption="Histograma de Cantidad de Ventas", use_container_width=True)
with col2:
    st.image("plots/heatmap_ventas_mexico.png", caption="Mapa de calor de ventas simuladas por estado - México", use_container_width=True)

# KPIs
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown('<div class="metric-card"><h3>Ganancia Total</h3><h2>$numero</h2><p>+20% mes a mes</p></div>', unsafe_allow_html=True)
with col2:
    st.markdown('<div class="metric-card"><h3>Ventas Total</h3><h2>2,numero</h2><p>+12% mes a mes</p></div>', unsafe_allow_html=True)
with col3:
    st.markdown('<div class="metric-card"><h3>Ventas Trimestrales Promedio</h3><h2>10,numero</h2><p>+1.2% mes a mes</p></div>', unsafe_allow_html=True)

# Top/Bottom 5
st.markdown("####  Top 5 / Bottom 5")
tab1, tab2 = st.tabs(["Top 5", "Bottom 5"])
with tab1:
    st.table(pd.DataFrame({
        "Producto": [f"P{i}" for i in range(1, 6)],
        "Ventas": np.random.randint(100, 500, 5)
    }))
with tab2:
    st.table(pd.DataFrame({
        "Producto": [f"P{i}" for i in range(6, 11)],
        "Ventas": np.random.randint(20, 100, 5)
    }))

# Gráfica de ventas y ganancia por categoría
st.image("plots/bar_ventas_ganancia.png", caption="Ventas y Ganancia por Categoría", use_container_width=True)
