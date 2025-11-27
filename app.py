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

global_data = process_data ()
data = global_data.copy()

categorias = pd.read_csv("data/categorias.csv")
categorias = list(categorias["nombre"])

# -----------------------------------------------------------
# VALORES PREDETERMINADOS
# -----------------------------------------------------------

today = datetime.date.today()
start_date = datetime.date(today.year, today.month, 1)
end_date = today
start_date = pd.to_datetime(start_date)
end_date   = pd.to_datetime(end_date)

global_data["fecha"] = pd.to_datetime(global_data["fecha"], errors="coerce")
data["fecha"] = pd.to_datetime(data["fecha"], errors="coerce")

is_in_period = ( start_date <= data["fecha"] ) & ( data["fecha"] <= end_date )
top_product= (
    data[is_in_period]
    .groupby("productId")["cantidad"]
    .sum()
    .idxmax()
)
product_list = list( data["productId"].unique() )
top_product_index = product_list.index(top_product)


is_top_product= data["productId"]==top_product
frequent_branch= (
    data[is_top_product]
    .groupby("sucursal")["fecha"]
    .nunique() 
    .idxmax()
)
branch_list = list( data[is_top_product]["sucursal"].unique() )
frequent_branch_index = branch_list.index(frequent_branch)

# -----------------------------------------------------------
# FILTROS
# -----------------------------------------------------------

st.sidebar.header("Filtros")
selected_categories = st.sidebar.multiselect("Categorías", data["category"].unique(),default=data["category"].unique())
is_category = data["category"].isin(selected_categories)


product = st.sidebar.selectbox("Producto", product_list ,index = top_product_index)


fecha_inicio = st.sidebar.date_input("Inicio", start_date)
fecha_fin = st.sidebar.date_input("Fin", today)
outliers= st.sidebar.radio("Análisis con ventas anomalas incluídas", ["No","Sí"])


is_product= data["productId"]==product
branch = st.sidebar.selectbox("Sucursal", branch_list, index=frequent_branch_index)


in_branch = global_data["sucursal"] == branch
data = global_data [in_branch].copy()


if outliers=="Sí":
    data = process_data()
else:
    data = gr.remove_outliers(data,"sales_day")

os.makedirs("plots", exist_ok=True)


# -----------------------------------------------------------
stock_vs_sales = gr.stock_vs_sales(data,product,start_date=fecha_inicio,end_date=fecha_fin)
histogram = gr.sales_hist(data[["sales_day","fecha"]],start_date=fecha_inicio,end_date=fecha_fin)
heat_map = gr.sales_heat_map(global_data,product,start_date=fecha_inicio,end_date=fecha_fin)
product_priorities = gr.abc_bar_chart(data,fecha_inicio,fecha_fin,type="productos")
category_priorities = gr.abc_bar_chart(data,fecha_inicio,fecha_fin,type="categorias")
sales_velocity = gr.stockCov_vs_salesVel(data[is_category],start_date=fecha_inicio,end_date=fecha_fin)

# -----------------------------------------------------------
# VISUALIZACIÓN EN STREAMLIT
# -----------------------------------------------------------


col1, col2 = st.columns(2)
with col1:
    st.pyplot(stock_vs_sales)
with col2:
    st.pyplot(sales_velocity)

# -----------------------------------------------------------
# INFO DE PRODUCTO
# -----------------------------------------------------------


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
    st.pyplot(histogram)
with col2:
    st.pyplot(heat_map)
# -----------------------------------------------------------
# KPIs
# -----------------------------------------------------------


total_sales = data[is_product]["cantidad"].sum()
total_cost = total_sales*data[is_product]["cost"].iloc[0]
total_profit = round( data[is_product]["income"].sum() - total_cost ,2 )
inventory_t_ratio = 0

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(f'<div class="metric-card"><h3>Costo Total</h3><h2>${total_cost}</h2><p>+ ritmo ejemplo</p></div>', unsafe_allow_html=True)
with col2:
    st.markdown(f'<div class="metric-card"><h3>Ventas Total</h3><h2>{total_sales}</h2><p>+ ritmo ejemplo</p></div>', unsafe_allow_html=True)
with col3:
    st.markdown(f'<div class="metric-card"><h3>Ganancia Total</h3><h2>{total_profit}</h2><p>+ ritmo ejemplo</p></div>', unsafe_allow_html=True)
with col4:
    st.markdown(f'<div class="metric-card"><h3>Cociente de Inventario</h3><h2>{inventory_t_ratio}</h2><p>+ ritmo ejemplo</p></div>', unsafe_allow_html=True)




# -----------------------------------------------------------
# PRIORIDADES
# -----------------------------------------------------------


col1, col2 = st.columns(2)
with col1:
    st.pyplot(product_priorities)
with col2:
    st.pyplot(category_priorities)
