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

st.markdown('<div class="main-header"> Inventario CT International</div>', unsafe_allow_html=True)
# -----------------------------------------------------------
# CARGA DE DATOS
# -----------------------------------------------------------

data = process_data ()
global_data = data.copy()
categorias = pd.read_csv("data/categorias.csv")
categorias = list(categorias["nombre"])

# -----------------------------------------------------------
# FILTROS
# -----------------------------------------------------------

st.sidebar.header("Filtros")
selected_categories = st.sidebar.multiselect("Categorías", data["category"].unique(),default=data["category"].unique())
is_category = data["category"].isin(selected_categories)


product = st.sidebar.selectbox("Producto", data[is_category]["productId"].unique())

today = datetime.date.today()
fecha_inicio = st.sidebar.date_input("Inicio", datetime.date(today.year, today.month, 1))
fecha_fin = st.sidebar.date_input("Fin", today)
outliers= st.sidebar.radio("Análisis con ventas anomalas incluídas", ["No","Sí"])


is_product= data["productId"]==product
branches = list( data[is_product]["sucursal"].unique() )
branch = st.sidebar.selectbox("Sucursal", branches,index=0)


os.makedirs("plots", exist_ok=True)

# -----------------------------------------------------------

if branch:
    in_branch = data["sucursal"] == branch
    data = data [in_branch]
else:
    data = process_data()

if outliers=="Sí":
    data = process_data()
else:
    data = gr.remove_outliers(data,"sales_day")



# -----------------------------------------------------------
stock_vs_sales = gr.stock_v_sales(data,product,start_date=fecha_inicio,end_date=fecha_fin)
gr.sales_hist(data[["sales_day","fecha"]],start_date=fecha_inicio,end_date=fecha_fin)
gr.sales_heat_map(global_data,product,start_date=fecha_inicio,end_date=fecha_fin)
gr.abc_bar_chart(data,fecha_inicio,fecha_fin,type="productos")
gr.abc_bar_chart(data,fecha_inicio,fecha_fin,type="categorias")
gr.stockCov_vs_salesVel(data[is_category],start_date=fecha_inicio,end_date=fecha_fin)

# -----------------------------------------------------------
# VISUALIZACIÓN EN STREAMLIT
# -----------------------------------------------------------


col1, col2 = st.columns(2)
with col1:
    st.pyplot(stock_vs_sales)
with col2:
    st.image("plots/almacen_v_rapidez_ventas.png", caption="Stock Cover vs Rápidez de Ventas", use_container_width=True)



# Info del producto

category = data[is_product]["category"].iloc[0]
top_clients = list ( gr.top_n(data[is_product],type="cliente")["client"] )

clients_str=''
for client in top_clients:
    clients_str+=client+','
clients_str = clients_str[:-1]

top_day = gr.top_day(data[is_product])
top_month = gr.top_month(data[is_product])

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(f"**Código:** {product}")
    st.markdown(f"**Categoría:** {category}")
with col2:
    st.markdown(f"**Mes más vendido:** {top_month}")
    st.markdown(f"**Día más vendido:** {top_day}")
with col3:
    st.markdown(f"**Clientes frecuentes:** {clients_str}")

# Histograma y mapa
col1, col2 = st.columns(2)
with col1:
    st.image("plots/hist_ventas_prod.png", caption="Histograma de Cantidad de Ventas", use_container_width=True)
with col2:
    st.image("plots/heatmap_ventas_mexico.png", caption="Mapa de calor de ventas simuladas por estado - México", use_container_width=True)

# KPIs

total_profit =round( data[is_product]["profit"].sum() ,2 )
total_sales = data[is_product]["sales_day"].sum()
total_cost = 0
inventory_t_ratio =0
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(f'<div class="metric-card"><h3>Costo Total</h3><h2>${total_cost}</h2><p>+ ritmo ejemplo</p></div>', unsafe_allow_html=True)
with col2:
    st.markdown(f'<div class="metric-card"><h3>Ventas Total</h3><h2>{total_sales}</h2><p>+ ritmo ejemplo</p></div>', unsafe_allow_html=True)
with col3:
    st.markdown(f'<div class="metric-card"><h3>Ganancia Total</h3><h2>{total_profit}</h2><p>+ ritmo ejemplo</p></div>', unsafe_allow_html=True)
with col4:
    st.markdown(f'<div class="metric-card"><h3>Cociente de Inventario</h3><h2>{inventory_t_ratio}</h2><p>+ ritmo ejemplo</p></div>', unsafe_allow_html=True)




# Gráfica de ventas y ganancia por categoría

col1, col2 = st.columns(2)
with col1:
    st.image("plots/productos_abc_chart.png", caption="Ventas Totales por Producto", use_container_width=True)
with col2:
    st.image("plots/categorias_abc_chart.png", caption="Ventas Totales por Producto", use_container_width=True)