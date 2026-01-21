import streamlit as st
import pandas as pd
import datetime
from src.graphs import *
from src.data_loader import *
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

global_data = process_data (update=True)
global_data["income"] = global_data["price"] * global_data["quantity"]

data = global_data.copy()
data["sales_day"]   = data.groupby(["productId", "date"])["quantity"].transform("sum")
data = remove_outliers(data,"sales_day")

inventory = load_inventory()

# -----------------------------------------------------------
# VALORES PREDETERMINADOS
# -----------------------------------------------------------

today = datetime.date.today() 
start_date = datetime.date(today.year, today.month, 1)
end_date = today 
start_date = pd.to_datetime(start_date)
end_date   = pd.to_datetime(end_date)

global_data["date"] = pd.to_datetime(global_data["date"], errors="coerce")
data["date"] = pd.to_datetime(data["date"], errors="coerce")

# Producto con cantidad de unidades más vendidas dentro de periodo
is_in_period = ( start_date <= data["date"] ) & ( data["date"] <= end_date )
top_product= (
    data[is_in_period]
    .groupby("productId")["quantity"]
    .sum()
    .idxmax()
)
product_list = list( data["productId"].unique() )
top_product_index = product_list.index(top_product)

# Sucursal en donde se vende más seguido el producto más vendido
is_top_product= data["productId"]==top_product
frequent_branch= (
    data[is_top_product]
    .groupby("sucursal")["date"]
    .nunique() 
    .idxmax()
)
branch_list = list( data["sucursal"].unique() )
frequent_branch_index = branch_list.index(frequent_branch)


top_category= (
    data[is_in_period]
    .groupby("category")["quantity"]
    .sum()
    .idxmax()
)
category_list = list( data["category"].unique() )
top_category_index = category_list.index(top_category)


# -----------------------------------------------------------
# FILTROS
# -----------------------------------------------------------

st.sidebar.header("Filtros")

analysis_lvl = st.sidebar.radio("Nivel de análisis",options=["Productos","Categorías"] )

if analysis_lvl=="Categorías":
    products = []
    categories = st.sidebar.multiselect(label="Categorías",options= data["category"].unique(),default=[top_category] ,max_selections=4)
    main_element = st.sidebar.radio("Categoría de análisis",options=categories)

if analysis_lvl=="Productos":
    categories = []
    products = st.sidebar.multiselect("Producto(s)", product_list ,
                                    default = [ top_product ],
                                    max_selections= 4 )
    main_element = st.sidebar.radio("Producto de análisis",options= products)


fecha_inicio = st.sidebar.date_input("Inicio", start_date)
fecha_fin = st.sidebar.date_input("Fin", today)
fecha_inicio = pd.to_datetime(fecha_inicio)
fecha_fin   = pd.to_datetime(fecha_fin)

outliers= st.sidebar.radio("Análisis con ventas anomalas incluídas", ["No","Sí"])


branch = st.sidebar.selectbox("Sucursal", branch_list, index=frequent_branch_index)

selected_elements = {"Productos":products,
                     "Categorías":categories}[analysis_lvl]
element_column = {"Productos":"productId",
                  "Categorías":"category"}[analysis_lvl]

is_category = data["category"].isin(categories)
in_branch = global_data["sucursal"] == branch
in_elements= global_data[element_column].isin(selected_elements)
is_global_element = global_data[element_column]==main_element
is_in_period = ( fecha_inicio <= global_data["date"] ) & ( global_data["date"] <= fecha_fin )

data = global_data [in_branch & in_elements & is_in_period].copy()
is_element = data[element_column]== main_element

data["sales_day"]   = data.groupby([element_column, "date"])["quantity"].transform("sum")
data["date"] = pd.to_datetime(data["date"])
data["month"] = data["date"].dt.month
data["year"] = data["date"].dt.year
data["income"] = data["price"] * data["quantity"]


if outliers=="Sí":
    data = process_data()

if data.empty:
    print("Dataset vacío")
        




# -----------------------------------------------------------
# GRÁFICAS
# -----------------------------------------------------------

period_sales_fig = period_sales(data=data,
                               selected_elements=selected_elements,
                               element_column=element_column,
                               branch=branch,
                               start_date=fecha_inicio,end_date=fecha_fin)

period_inventory_fig = period_inventory(data=inventory,
                               selected_elements=selected_elements,
                               element_column=element_column,
                               branch=branch,
                               start_date=fecha_inicio,end_date=fecha_fin)


sales_velocity_fig = sales_velocity(data=data,
                                   selected_elements=selected_elements,
                                   element_column=element_column,
                                   branch=branch,
                                   start_date=fecha_inicio,end_date=fecha_fin)


histogram = sales_hist(data=data,
                          main_element=main_element,
                          element_column=element_column,
                          branch=branch,
                          start_date=fecha_inicio,end_date=fecha_fin)


product_priorities = abc_bar_chart(data=global_data,
                                      branch=branch,
                                      start_date=fecha_inicio,end_date=fecha_fin,type="productos")

category_priorities = abc_bar_chart(data=global_data,
                                      branch=branch,
                                      start_date=fecha_inicio,end_date=fecha_fin,type="categorias")

# -----------------------------------------------------------
# VENTAS Y RÁPIDEZ DE VENTAS
# -----------------------------------------------------------


col1, col2 = st.columns(2)
with col1:
    st.pyplot(period_sales_fig)
with col2:
    st.pyplot(period_inventory_fig)

# -----------------------------------------------------------
# INFO DE PRODUCTO
# -----------------------------------------------------------

cost_per_unit = round(data["cost"].iloc[0],2)
price_range =( round(data["price"].min(),2) , round( data["price"].max(),2) )
category = data[is_element]["category"].iloc[0]
top_clients = list ( top_n(data[is_element],type="cliente")["clientId"] )

clients_str=''
for client in top_clients:
    clients_str+=client+','
clients_str = clients_str[:-1]

top_day = top_day(data[is_element])
top_month = top_month(data[is_element])

col1, col2, col3 = st.columns(3)
with col1:
    if analysis_lvl=="Productos":
        st.markdown(f"**Código:** {main_element}")
    
    st.markdown(f"**Categoría:** {category}")
    
with col2:
    if analysis_lvl=="Productos":
        st.markdown(f"**Costo por unidad:** $ {cost_per_unit}")

        if price_range[0]==price_range[1]:
            st.markdown(f"**Precio por unidad:** $ {price_range[0]}")
        else:
            st.markdown(f"**Rango de precios:** $ {price_range[0]} - $ {price_range[1]}")

with col3:
    st.markdown(f"**Clientes frecuentes:** {clients_str}")
    st.markdown(f"**Mes más vendido:** {top_month}")
    st.markdown(f"**Día más vendido:** {top_day}")

# -----------------------------------------------------------
# HISTOGRAMA Y MAPA CALOR
# -----------------------------------------------------------




col1, col2 = st.columns(2)
with col1:
    st.pyplot(histogram)
with col2:

    merged= prepare_sales_heatmap_data(
    global_data,
    main_element,
    element_column,
    start_date,
    end_date,
)

    map_obj, selected_state = render_sales_heat_map(merged, main_element)

# -----------------------------------------------------------
# KPIs (SUCURSAL)
# -----------------------------------------------------------


total_branch_sales = round ( data[is_element]["quantity"].sum() ,2 )
total_branch_cost = round ( data[is_element]["cost"].sum() ,2 )
total_branch_profit = round( data[is_element]["income"].sum() - total_branch_cost ,2 )
branch_inventory_t_ratio = 0

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(f'<div class="metric-card"><h3>Ventas Totales</h3><h2>{total_branch_sales:,}</h2><p>+ ritmo ejemplo</p></div>', unsafe_allow_html=True)
with col2:
    st.markdown(f'<div class="metric-card"><h3>Ganancia Total</h3><h2>${total_branch_profit:,}</h2><p>+ ritmo ejemplo</p></div>', unsafe_allow_html=True)
with col3:
    st.markdown(f'<div class="metric-card"><h3>Costo Total</h3><h2>${total_branch_cost:,}</h2><p>+ ritmo ejemplo</p></div>', unsafe_allow_html=True)



# -----------------------------------------------------------
# KPIs (GLOBAL)
# -----------------------------------------------------------


total_sales = round( global_data [is_global_element & is_in_period]["quantity"].sum() , 2 )
total_cost = round( global_data [is_global_element & is_in_period]["cost"].sum() , 2 )
total_profit = round( global_data [is_global_element & is_in_period]["income"].sum() - total_cost ,2 )
inventory_t_ratio = 0

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(f'<div class="metric-card"><h3>Ventas Totales</h3><h2>{total_sales:,}</h2><p>+ ritmo ejemplo</p></div>', unsafe_allow_html=True)
with col2:
    st.markdown(f'<div class="metric-card"><h3>Ganancia Total</h3><h2>${total_profit:,}</h2><p>+ ritmo ejemplo</p></div>', unsafe_allow_html=True)
with col3:
    st.markdown(f'<div class="metric-card"><h3>Costo Total</h3><h2>${total_cost:,}</h2><p>+ ritmo ejemplo</p></div>', unsafe_allow_html=True)



# -----------------------------------------------------------
# PRIORIDADES
# -----------------------------------------------------------


col1, col2 = st.columns(2)
with col1:
    st.pyplot(product_priorities)
with col2:
    st.pyplot(category_priorities)
