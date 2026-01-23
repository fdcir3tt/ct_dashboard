import streamlit as st
import pandas as pd
import datetime
from src.graphs import *
from src.data_loader import *
from src.preprocess import process_data

# -----------------------------------------------------------
# CONFIGURACIÓN INICIAL
# -----------------------------------------------------------

def pick_date(label: str, default: datetime.date = None, key: str = "selected_date"):
    
    if key not in st.session_state:
        st.session_state[key] = default
    
    return st.date_input(label, value=st.session_state[key], key=key)


def pick_elements(label: str,options:list,default: list[str]= None, key: str = "selected_elements"):
    if key not in st.session_state:
        st.session_state[key] = default
    return st.multiselect(label, options ,
                                    default = default,
                                    max_selections= 4 ,
                                    key=key)
    

def pick_main_element(label: str,options:list,default: str= None, key: str = "selected_element"):
    if key not in st.session_state:
        st.session_state[key] = default
    
    return st.radio(label=label,options= options ,key=key)


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
outliers= st.sidebar.radio("Análisis con ventas anomalas incluídas", ["No","Sí"])
branch = st.sidebar.selectbox("Sucursal", branch_list, index=frequent_branch_index)


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



tab1, tab2 = st.tabs(["Ventas","Inventario"])

# -----------------------------------------------------------
# ANÁLISIS VENTAS
# -----------------------------------------------------------

with tab1:
    left, right = st.columns([1.2, 3])

    with left:

        
# -----------------------------------------------------------
# INFO DE PRODUCTO/CATEGORIA
# -----------------------------------------------------------

        
        if analysis_lvl=="Productos":
            categories = []
            products = pick_elements(label="Producto(s)",options=product_list,default=[top_product],key="Sucursal Productos Seleccionados")
            main_element = pick_main_element(label="Producto de análisis",options= products,key="producto de análisis")
            st.markdown(f"**Producto:** {main_element}")

        if analysis_lvl=="Categorías":
            products = []
            categories = pick_elements(label="Categoría(s)",options=category_list,default=[top_category],key="Sucursal Categorías Seleccionadas")
            main_element = pick_main_element(label="Categoría de análisis",options= categories,key="categoría de análisis")
            st.markdown(f"**Categoría:** {main_element}")
        
        
        selected_elements = {"Productos":products,
                            "Categorías":categories}[analysis_lvl]
        element_column = {"Productos":"productId",
                        "Categorías":"category"}[analysis_lvl]

        is_global_element = global_data[element_column]==main_element
        is_element = data[element_column]== main_element
        

        st.markdown("### Periodo")
        period_start = pick_date(label="Inicio",default=period_start,key="Sucursal Inicio")
        period_end = pick_date(label="Fin",default=period_end,key="Sucursal Fin")

        filtered = data[is_element]
        if filtered.empty:
            st.warning("No hay datos para el elemento seleccionado en este periodo.")
            st.stop()

        cost_per_unit = round(filtered["cost"].iloc[0],2)
        price_range =( round(filtered["price"].min(),2) , round( filtered["price"].max(),2) )
        category = filtered["category"].iloc[0]
        top_clients = list ( top_n(filtered,element_column,type="cliente")["clientId"] )

        clients_str=''
        for client in top_clients:
            clients_str+=client+','
        clients_str = clients_str[:-1]


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
# SUCURSAL Y GLOBAL 
# -----------------------------------------------------------
        
        branch_period_sales_fig = period_sales(data=data,
                                    selected_elements=selected_elements,
                                    element_column=element_column,
                                    branch=branch,
                                    start_date=period_start,end_date=period_end)
        global_period_sales_fig = period_sales(data=data,
                                    selected_elements=selected_elements,
                                    element_column=element_column,
                                    start_date=period_start,end_date=period_end)

        
        st.markdown("### Ventas Diarias")
        
        col1, col2 = st.columns(2)
        with col1:
            st.pyplot(branch_period_sales_fig)
        with col2:
            st.pyplot(global_period_sales_fig)

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
# KPIs (VENTAS)
# -----------------------------------------------------------
        filtered = data[is_element]

        if filtered.empty:
            st.warning("No hay datos para el elemento seleccionado en este periodo.")
            st.stop()

        total_branch_sales = round ( filtered["quantity"].sum() ,2 )
        total_branch_cost = round ( filtered["cost"].sum() ,2 )
        total_branch_profit = round( filtered["income"].sum() - total_branch_cost ,2 )
        branch_inventory_t_ratio = 0

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f'<div class="kpi-title"><h3>Unidades Vendidas</h3><h2>{total_branch_sales:,}</h2><p>+ ritmo ejemplo</p></div>', unsafe_allow_html=True)
        with col2:
            st.markdown(f'<div class="kpi-title"><h3>Ganancia (MXN)</h3><h2>${total_branch_profit:,}</h2><p>+ ritmo ejemplo</p></div>', unsafe_allow_html=True)
        with col3:
            st.markdown(f'<div class="kpi-title"><h3>Costo (MXN) </h3><h2>${total_branch_cost:,}</h2><p>+ ritmo ejemplo</p></div>', unsafe_allow_html=True)



# -----------------------------------------------------------
# PRIORIDADES
# -----------------------------------------------------------
        
        product_priorities = abc_bar_chart(data=global_data,
                                            branch=branch,
                                            start_date=period_start,end_date=period_end,type="productos")

        category_priorities = abc_bar_chart(data=global_data,
                                            branch=branch,
                                            start_date=period_start,end_date=period_end,type="categorias")

        
        if analysis_lvl=="Productos":
            st.pyplot(product_priorities)
        if analysis_lvl=="Categorías":
            st.pyplot(category_priorities)
            
        




# -----------------------------------------------------------
# ANÁLISIS INVENTARIO
# -----------------------------------------------------------
with tab2:

   left, right = st.columns([1.2, 3])

   with left:

        
# -----------------------------------------------------------
# INFO DE PRODUCTO/CATEGORIA
# -----------------------------------------------------------
        filtered = data[is_element]

        if filtered.empty:
            st.warning("No hay datos para el elemento seleccionado en este periodo.")
            st.stop()
        cost_per_unit = round(data["cost"].iloc[0],2)
        price_range =( round(data["price"].min(),2) , round( data["price"].max(),2) )
        category = filtered["category"].iloc[0]
        top_clients = list ( top_n(filtered,element_column,type="cliente")["clientId"] )

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

        st.markdown("Periodo")
        period_start_global = pick_date(label="Inicio",default=period_start,key="Global Inicio")
        period_end_global = pick_date(label="Fin",default=period_end,key="Global Fin")

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
        
        branch_period_inventory_fig = period_inventory(data=inventory,
                                    selected_elements=selected_elements,
                                    element_column=element_column,
                                    branch=branch,
                                    start_date=period_start_global,end_date=period_end_global)

        global_period_inventory_fig = period_inventory(data=inventory,
                                    selected_elements=selected_elements,
                                    element_column=element_column,
                                    start_date=period_start_global,end_date=period_end_global)
        st.markdown("### Existencia Diaria")
        col1, col2 = st.columns(2)
        with col1:
            st.pyplot(branch_period_inventory_fig)
        with col2:
            st.pyplot(global_period_inventory_fig)


# -----------------------------------------------------------
# HISTOGRAMA Y MAPA CALOR
# -----------------------------------------------------------

        c1, c2 = st.columns(2)

        with c1:
                histogram = sales_hist(data=data,
                          main_element=main_element,
                          element_column=element_column,
                          branch=branch,
                          start_date=period_start_global,end_date=period_end_global)

                st.markdown("**Histograma de Ventas**")
                st.pyplot(histogram)

        with c2:
                st.markdown("**Mapa de calor de ventas (México)**")
                merged = prepare_sales_heatmap_data(
                                                    global_data,
                                                    main_element,
                                                    element_column,
                                                    period_start_global,
                                                    period_end_global,
                                                )

                map_obj, selected_state = render_sales_heat_map(merged, main_element,map_key="Global Mapa")



# -----------------------------------------------------------
# KPIs (INVENTARIO)
# -----------------------------------------------------------
        filtered = global_data [is_global_element & is_in_period]

        if filtered.empty:
            st.warning("No hay datos para el elemento seleccionado en este periodo.")
            st.stop()

        total_sales = round( filtered["quantity"].sum() , 2 )
        total_cost = round( filtered["cost"].sum() , 2 )
        total_profit = round( filtered["income"].sum() - total_cost ,2 )
        

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f'<div class="kpi-title"><h3>Unidades Vendidas</h3><h2>{total_sales:,} </h2><p>+ ritmo ejemplo</p></div>', unsafe_allow_html=True)
        with col2:
            st.markdown(f'<div class="kpi-title"><h3>Ganancia Total (MXN)</h3><h2>${total_profit:,} </h2><p>+ ritmo ejemplo</p></div>', unsafe_allow_html=True)
        with col3:
            st.markdown(f'<div class="kpi-title"><h3>Costo Total (MXN)</h3><h2>${total_cost:,}</h2><p>+ ritmo ejemplo</p></div>', unsafe_allow_html=True)




# -----------------------------------------------------------
# PRIORIDADES
# -----------------------------------------------------------

        product_priorities = abc_bar_chart(data=global_data,
                                            branch=branch,
                                            start_date=period_start_global,end_date=period_end_global,type="productos")

        category_priorities = abc_bar_chart(data=global_data,
                                            branch=branch,
                                            start_date=period_start_global,end_date=period_end_global,type="categorias")

        
        
        if analysis_lvl=="Productos":
            st.pyplot(product_priorities)
        if analysis_lvl=="Categorías":
            st.pyplot(category_priorities)



