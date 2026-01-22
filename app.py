import streamlit as st
import pandas as pd
import datetime
from src.graphs import *
from src.data_loader import *
from src.preprocess import process_data

# -----------------------------------------------------------
# CONFIGURACIÓN INICIAL
# -----------------------------------------------------------

def load_css(file_name):
    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


st.set_page_config(page_title="Inventario CT International", layout="wide")

load_css("assets/styles.css")



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
period_start = pd.to_datetime( datetime.date(today.year, today.month, 1) )
period_end = pd.to_datetime( today )

global_data["date"] = pd.to_datetime(global_data["date"], errors="coerce")
data["date"] = pd.to_datetime(data["date"], errors="coerce")

# Producto con cantidad de unidades más vendidas dentro de periodo
is_in_period = ( period_start <= data["date"] ) & ( data["date"] <= period_end )
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
is_in_period = ( period_start <= global_data["date"] ) & ( global_data["date"] <= period_end )

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
# LOGO Y TITULO
# -----------------------------------------------------------

col1, col2 = st.columns([1, 8])
with col1:
    st.image("assets/logo.png", width=50)

with col2:
    st.markdown("### Inventario CT International")




tab1, tab2 = st.tabs(["Sucursal","Global"])

# -----------------------------------------------------------
# ANÁLISIS NIVEL SUCURSAL
# -----------------------------------------------------------

with tab1:
    left, right = st.columns([1.2, 3])

    with left:

        
# -----------------------------------------------------------
# INFO DE PRODUCTO/CATEGORIA
# -----------------------------------------------------------
        
        cost_per_unit = round(data["cost"].iloc[0],2)
        price_range =( round(data["price"].min(),2) , round( data["price"].max(),2) )
        category = data[is_element]["category"].iloc[0]
        top_clients = list ( top_n(data[is_element],type="cliente")["clientId"] )

        clients_str=''
        for client in top_clients:
            clients_str+=client+','
        clients_str = clients_str[:-1]

        

        products = st.multiselect("Producto(s)", product_list ,
                                    default = [ top_product ],
                                    max_selections= 4 ,
                                    key="Sucursal")
        if analysis_lvl=="Productos":
            st.markdown(f"**Producto:** {main_element}")

        if analysis_lvl=="Categorías":
            st.markdown(f"**Categoría:** {main_element}")

        st.markdown("### Periodo")
        period_start = st.date_input("Inicio",period_start,key="Sucursal Inicio")
        period_end = st.date_input("Fin",period_end,key="Sucursal Fin")

        if analysis_lvl=="Productos":
    
            st.table(pd.DataFrame({
                "": [
                    "Código",
                    "Categoría",
                    "Costo por unidad(MXN)",
                    "Precio por unidad(MXN)",
                    "Clientes frecuentes"
                ],
                "Valor": [
                    main_element,
                    category,
                    cost_per_unit,
                    price_range[0],
                    clients_str
                ]
            }))
        if analysis_lvl=="Categorías":
        
            st.table(pd.DataFrame({
                "": [
                    "Categoría",
                    "Clientes frecuentes"
                ],
                "Valor": [
                    category,
                    clients_str
                ]
            }))
    with right:

# -----------------------------------------------------------
# VENTAS O INVENTARIO
# -----------------------------------------------------------
        
        period_sales_fig = period_sales(data=data,
                                    selected_elements=selected_elements,
                                    element_column=element_column,
                                    branch=branch,
                                    start_date=period_start,end_date=period_end)

        period_inventory_fig = period_inventory(data=inventory,
                                    selected_elements=selected_elements,
                                    element_column=element_column,
                                    branch=branch,
                                    start_date=period_start,end_date=period_end)
        st.markdown("### Ventas Diarias")
        st.pyplot(period_sales_fig)


# -----------------------------------------------------------
# HISTOGRAMA Y MAPA CALOR
# -----------------------------------------------------------

        c1, c2 = st.columns(2)

        with c1:
                histogram = sales_hist(data=data,
                          main_element=main_element,
                          element_column=element_column,
                          branch=branch,
                          start_date=period_start,end_date=period_end)

                st.markdown("**Histograma de Ventas**")
                st.pyplot(histogram)

        with c2:
                st.markdown("**Mapa de calor de ventas (México)**")
                merged = prepare_sales_heatmap_data(
                                                    global_data,
                                                    main_element,
                                                    element_column,
                                                    period_start,
                                                    period_end,
                                                )

                map_obj, selected_state = render_sales_heat_map(merged, main_element,map_key="Sucursal Mapa")


# -----------------------------------------------------------
# KPIs (SUCURSAL)
# -----------------------------------------------------------


        total_branch_sales = round ( data[is_element]["quantity"].sum() ,2 )
        total_branch_cost = round ( data[is_element]["cost"].sum() ,2 )
        total_branch_profit = round( data[is_element]["income"].sum() - total_branch_cost ,2 )
        branch_inventory_t_ratio = 0

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f'<div class="kpi-title"><h3>Unidades Vendidas</h3><h2>{total_branch_sales:,}</h2><p>+ ritmo ejemplo</p></div>', unsafe_allow_html=True)
        with col2:
            st.markdown(f'<div class="kpi-title"><h3>Ganancia </h3><h2>${total_branch_profit:,}</h2><p>+ ritmo ejemplo</p></div>', unsafe_allow_html=True)
        with col3:
            st.markdown(f'<div class="kpi-title"><h3>Costo </h3><h2>${total_branch_cost:,}</h2><p>+ ritmo ejemplo</p></div>', unsafe_allow_html=True)



# -----------------------------------------------------------
# PRIORIDADES
# -----------------------------------------------------------

        product_priorities = abc_bar_chart(data=global_data,
                                            branch=branch,
                                            start_date=period_start,end_date=period_end,type="productos")

        category_priorities = abc_bar_chart(data=global_data,
                                            branch=branch,
                                            start_date=period_start,end_date=period_end,type="categorias")

        col1, col2 = st.columns(2)
        with col1:
            st.pyplot(product_priorities)
        with col2:
            st.pyplot(category_priorities)




# -----------------------------------------------------------
# ANÁLISIS NIVEL GLOBAL
# -----------------------------------------------------------
with tab2:

   left, right = st.columns([1.2, 3])

   with left:

        
# -----------------------------------------------------------
# INFO DE PRODUCTO/CATEGORIA
# -----------------------------------------------------------
        
        cost_per_unit = round(data["cost"].iloc[0],2)
        price_range =( round(data["price"].min(),2) , round( data["price"].max(),2) )
        category = data[is_element]["category"].iloc[0]
        top_clients = list ( top_n(data[is_element],type="cliente")["clientId"] )

        clients_str=''
        for client in top_clients:
            clients_str+=client+','
        clients_str = clients_str[:-1]


        products = st.multiselect("Producto(s)", product_list ,
                                    default = [ top_product ],
                                    max_selections= 4 )
        if analysis_lvl=="Productos":
            st.markdown(f"**Producto:** {main_element}")

        if analysis_lvl=="Categorías":
            st.markdown(f"**Categoría:** {main_element}")

        st.markdown("### Periodo")
        period_start = st.date_input("Inicio",period_start)
        period_end = st.date_input("Fin",period_end)

        if analysis_lvl=="Productos":
    
            st.table(pd.DataFrame({
                "": [
                    "Código",
                    "Categoría",
                    "Costo por unidad(MXN)",
                    "Precio por unidad(MXN)",
                    "Clientes frecuentes"
                ],
                "Valor": [
                    main_element,
                    category,
                    cost_per_unit,
                    price_range[0],
                    clients_str
                ]
            }))
        if analysis_lvl=="Categorías":
        
            st.table(pd.DataFrame({
                "": [
                    "Categoría",
                    "Clientes frecuentes"
                ],
                "Valor": [
                    category,
                    clients_str
                ]
            }))
   with right:

# -----------------------------------------------------------
# VENTAS O INVENTARIO
# -----------------------------------------------------------
        
        period_sales_fig = period_sales(data=data,
                                    selected_elements=selected_elements,
                                    element_column=element_column,
                                    branch=branch,
                                    start_date=period_start,end_date=period_end)

        period_inventory_fig = period_inventory(data=inventory,
                                    selected_elements=selected_elements,
                                    element_column=element_column,
                                    branch=branch,
                                    start_date=period_start,end_date=period_end)
        st.markdown("### Ventas Diarias")
        st.pyplot(period_sales_fig)


# -----------------------------------------------------------
# HISTOGRAMA Y MAPA CALOR
# -----------------------------------------------------------

        c1, c2 = st.columns(2)

        with c1:
                histogram = sales_hist(data=data,
                          main_element=main_element,
                          element_column=element_column,
                          branch=branch,
                          start_date=period_start,end_date=period_end)

                st.markdown("**Histograma de Ventas**")
                st.pyplot(histogram)

        with c2:
                st.markdown("**Mapa de calor de ventas (México)**")
                merged = prepare_sales_heatmap_data(
                                                    global_data,
                                                    main_element,
                                                    element_column,
                                                    period_start,
                                                    period_end,
                                                )

                map_obj, selected_state = render_sales_heat_map(merged, main_element,map_key="Global Mapa")



# -----------------------------------------------------------
# KPIs (GLOBAL)
# -----------------------------------------------------------


        total_sales = round( global_data [is_global_element & is_in_period]["quantity"].sum() , 2 )
        total_cost = round( global_data [is_global_element & is_in_period]["cost"].sum() , 2 )
        total_profit = round( global_data [is_global_element & is_in_period]["income"].sum() - total_cost ,2 )
        inventory_t_ratio = 0

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f'<div class="kpi-title"><h3>Unidades Vendidas</h3><h2>{total_sales:,}</h2><p>+ ritmo ejemplo</p></div>', unsafe_allow_html=True)
        with col2:
            st.markdown(f'<div class="kpi-title"><h3>Ganancia Total</h3><h2>${total_profit:,}</h2><p>+ ritmo ejemplo</p></div>', unsafe_allow_html=True)
        with col3:
            st.markdown(f'<div class="kpi-title"><h3>Costo Total</h3><h2>${total_cost:,}</h2><p>+ ritmo ejemplo</p></div>', unsafe_allow_html=True)




# -----------------------------------------------------------
# PRIORIDADES
# -----------------------------------------------------------

        product_priorities = abc_bar_chart(data=global_data,
                                            branch=branch,
                                            start_date=period_start,end_date=period_end,type="productos")

        category_priorities = abc_bar_chart(data=global_data,
                                            branch=branch,
                                            start_date=period_start,end_date=period_end,type="categorias")

        col1, col2 = st.columns(2)
        with col1:
            st.pyplot(product_priorities)
        with col2:
            st.pyplot(category_priorities)


