import streamlit as st
import pandas as pd
import datetime
from src.graphs import *
from src.data_loader import *
from src.preprocess import process_data

# -----------------------------------------------------------
# CONFIGURACIÓN INICIAL
# -----------------------------------------------------------

def pick_date(label: str, default: datetime.datetime = None, key: str = "selected_date"):
    
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

def growth_rate(current, previous):
    if previous == 0:
        return 0
    return round(((current - previous) / previous) * 100, 2)

st.set_page_config(page_title="Inventario CT International", layout="wide")

load_css("assets/styles.css")




# -----------------------------------------------------------
# CARGA DE DATOS
# -----------------------------------------------------------
invoices = load_invoices()
product_codes =load_product_codes()
exchange_rates = load_exchange_rates()
branches = load_branches()
categories = load_categories()
products = load_products()

global_data = process_data (invoices,product_codes,exchange_rates,branches,categories,products,update=True)
global_data["income"] = global_data["price"] * global_data["quantity"]

data = global_data.copy()
inventory = load_inventory()

# -----------------------------------------------------------
# VALORES PREDETERMINADOS
# -----------------------------------------------------------

today = datetime.date.today() 
period_start = pd.to_datetime( datetime.date(today.year, today.month, 1) )
period_end = pd.to_datetime( today )



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
    left, right = st.columns([1.3, 3.7])

    with left:

        
# -----------------------------------------------------------
# INFO DE PRODUCTO/CATEGORIA
# -----------------------------------------------------------
        if analysis_lvl=="Productos":
                categories = []
                products = pick_elements(label="Producto(s)",options=product_list,default=[top_product],key="Sucursal Productos Seleccionados")
        
        if analysis_lvl=="Categorías":
                products = []
                categories = pick_elements(label="Categoría(s)",options=category_list,default=[top_category],key="Sucursal Categorías Seleccionadas")
                
        col1,col2 = st.columns(2)
        with col1:

            if analysis_lvl=="Productos":
                main_element = pick_main_element(label="Producto de análisis",options= products,key="producto de análisis")
                element_title= f"**Producto:** {main_element}"

            if analysis_lvl=="Categorías":
                main_element = pick_main_element(label="Categoría de análisis",options= categories,key="categoría de análisis")
                element_title = f"**Categoría:** {main_element}"
                

        with col2:
            st.markdown(" Periodo")
            period_start = pick_date(label="Inicio",default=period_start,key="Sucursal Inicio")
            period_end = pick_date(label="Fin",default=period_end,key="Sucursal Fin")

        selected_elements = {"Productos":products,
                            "Categorías":categories}[analysis_lvl]
        element_column = {"Productos":"productId",
                        "Categorías":"category"}[analysis_lvl]

        is_global_element = global_data[element_column]==main_element
        is_element = data[element_column]== main_element
        in_branch = data["sucursal"]==branch

        

        filtered = data[is_element]
        if filtered.empty:
            st.warning("No hay datos para el elemento seleccionado en este periodo.")
            st.stop()

        cost_per_unit = round(filtered["cost"].max(),2)
        price_range =( round(filtered["price"].min(),2) , round( filtered["price"].max(),2) )
        category = filtered["category"].iloc[0]
        top_clients = list ( top_n(filtered,element_column,type="cliente")["clientId"] )

        clients_str=''
        for client in top_clients:
            clients_str+=client+','
        clients_str = clients_str[:-1]

        st.markdown(element_title)
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
                    price_range[1],
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
                branch_histogram = sales_hist(data=data,
                          main_element=main_element,
                          element_column=element_column,
                          branch=branch,
                          start_date=period_start,end_date=period_end)

                st.markdown(f"**{branch}**")
                st.pyplot(branch_histogram)

        with c2:
                global_histogram = sales_hist(data=data,
                          main_element=main_element,
                          element_column=element_column,
                          start_date=period_start,end_date=period_end)

                st.markdown("**Global**")
                st.pyplot(global_histogram)
                
                


# -----------------------------------------------------------
# KPIs (VENTAS)
# -----------------------------------------------------------
        filtered = data[is_element & is_in_period & in_branch].copy()

        if filtered.empty:
            st.warning("No hay datos para el elemento seleccionado en este periodo.")
            st.stop()

        total_branch_sales = round ( filtered["quantity"].sum() ,2 )
        total_branch_cost = round ( filtered["cost"].sum() ,2 )
        total_branch_profit = round( filtered["income"].sum() - total_branch_cost ,2 )
        branch_inventory_t_ratio = 0

        col1, col2, col3 = st.columns(3)
        previous_period = ( pd.to_datetime(period_start)-datetime.timedelta(days=30) <= filtered["date"] ) & ( filtered["date"] <= pd.to_datetime(period_start) ) 
        filtered_prev = filtered[previous_period]
        prev_sales = filtered_prev["quantity"].sum()
        prev_cost = filtered_prev["cost"].sum()
        prev_profit = filtered_prev["income"].sum() - prev_cost


        sales_rate = growth_rate(total_branch_sales, prev_sales)
        profit_rate = growth_rate(total_branch_profit, prev_profit)
        cost_rate = growth_rate(total_branch_cost, prev_cost)

        with col1:
            st.markdown(
                f'''
                <div class="kpi-title">
                    <h3>Unidades Vendidas</h3>
                    <h2>{total_branch_sales:,}</h2>
                    <p>{5:+}%</p>
                </div>
                ''',
                unsafe_allow_html=True
            )

        with col2:
            st.markdown(
                f'''
                <div class="kpi-title">
                    <h3>Ganancia (MXN)</h3>
                    <h2>${total_branch_profit:,}</h2>
                    <p>{2:+}%</p>
                </div>
                ''',
                unsafe_allow_html=True
            )

        with col3:
            st.markdown(
                f'''
                <div class="kpi-title">
                    <h3>Costo (MXN)</h3>
                    <h2>${total_branch_cost:,}</h2>
                    <p>{5:+}%</p>
                </div>
                ''',
                unsafe_allow_html=True
            )

        global_filtered = global_data [is_global_element & is_in_period].copy()

        if filtered.empty:
            st.warning("No hay datos para el elemento seleccionado en este periodo.")
            st.stop()

        total_sales = round( global_filtered["quantity"].sum() , 2 )
        total_cost = round( global_filtered["cost"].sum() , 2 )
        total_profit = round( global_filtered["income"].sum() - total_cost ,2 )
        

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f'''
                        <div class="kpi-title">
                            <h3>Unidades Vendidas</h3>
                            <h2>{total_sales:,} </h2>
                            <p>- {3.1}</p>
                        </div>
                        ''', 
                        unsafe_allow_html=True)
        with col2:
            st.markdown(f'''
                        <div class="kpi-title">
                            <h3>Ganancia Total (MXN)</h3>
                            <h2>${total_profit:,} </h2>
                            <p>+ {2}</p>
                        </div>
                        ''',
                        unsafe_allow_html=True)
        with col3:
            st.markdown(f'''
                        <div class="kpi-title">
                            <h3>Costo Total (MXN)</h3>
                            <h2>${total_cost:,}</h2>
                            <p>+{10}</p>
                        </div>''',
                        unsafe_allow_html=True)



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
                st.markdown("**Mapa de calor de ventas (México)**")
                merged = prepare_sales_heatmap_data(
                                                    global_data,
                                                    main_element,
                                                    element_column,
                                                    period_start,
                                                    period_end,
                                                )

                map_obj, selected_state = render_sales_heat_map(merged, main_element,map_key="Ventas Mapa")
        with col2:
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

        col1, col2 = st.columns(2)

        with col1:
                branch_histogram = sales_hist(data=data,
                          main_element=main_element,
                          element_column=element_column,
                          branch=branch,
                          start_date=period_start_global,end_date=period_end_global)

                st.markdown(f"**{branch}**")
                st.pyplot(branch_histogram)

        with col2:
                global_histogram = sales_hist(data=data,
                          main_element=main_element,
                          element_column=element_column,
                          start_date=period_start_global,end_date=period_end_global)

                st.markdown("**Global**")
                st.pyplot(global_histogram)

                



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
        col1, col2 = st.columns(2)
        with col1:
                st.markdown("**Mapa de calor de ventas (México)**")
                merged = prepare_sales_heatmap_data(
                                                    global_data,
                                                    main_element,
                                                    element_column,
                                                    period_start_global,
                                                    period_end_global,
                                                )

                map_obj, selected_state = render_sales_heat_map(merged, main_element,map_key="Global Mapa")
        with col2:
            if analysis_lvl=="Productos":
                st.pyplot(product_priorities)
            if analysis_lvl=="Categorías":
                st.pyplot(category_priorities)



