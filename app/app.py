import streamlit as st
import pandas as pd
import datetime
from functools import wraps
from ct_sales_dashboard.graphs import *
from ct_sales_dashboard.data_loader import *


st.set_page_config(
    page_title="CT Dashboard",
    layout="wide",  
    initial_sidebar_state="collapsed" 
)





def make_cached(func):
    """Crea versiones cacheadas de funciones"""
    @st.cache_data
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

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

def calculate_iqr_bounds(sales_series):
    q1 = sales_series.quantile(0.25)
    q3 = sales_series.quantile(0.75)
    iqr = q3 - q1
    return (q1 - 1.5 * iqr, q3 + 1.5 * iqr)


def identify_outlier_sales(data: pd.DataFrame,
                           element_column:str='productId')->pd.DataFrame:
    df = data.copy()

    bounds_dict = df.groupby(element_column)['quantity'].apply(calculate_iqr_bounds).to_dict()
    
    df['iqr_bounds'] = df[element_column].map(bounds_dict)
    df['is_outlier'] = df['quantity'].between(
                                              df['iqr_bounds'].str[0], 
                                              df['iqr_bounds'].str[1]
                                              )

    print('Ventas anomalas detectadas correctamente !')
    df = df.drop(columns='iqr_bounds')
    return df


st.set_page_config(page_title="Inventario CT International", layout="wide")
load_css("assets/styles.css")


# -----------------------------------------------------------
# CACHE WRAPPERS
# -----------------------------------------------------------

cached_load_branches = make_cached (load_branches)
cached_load_storage = make_cached(load_storage)
cached_load_inventory = make_cached(load_inventory)
cached_load_sales_invoices = make_cached(load_sales_invoices)
cached_identify_outlier_sales = make_cached (identify_outlier_sales)
cached_prepare_sales_heatmap_data = make_cached(prepare_sales_heatmap_data)

# -----------------------------------------------------------
# CARGA DE DATOS
# -----------------------------------------------------------

branch_storage = cached_load_storage()
inventory = cached_load_inventory()

global_data = cached_load_sales_invoices()
global_data['income'] = global_data['price'] * global_data['quantity']
global_data = cached_identify_outlier_sales(global_data)


data = global_data.copy()


# -----------------------------------------------------------
# VALORES PREDETERMINADOS
# -----------------------------------------------------------

today = datetime.date.today() 
period_start = pd.to_datetime( datetime.date(today.year, today.month, 1) )
period_end = pd.to_datetime( today )



# Producto con cantidad de unidades más vendidas dentro de periodo
is_in_period = ( period_start <= data["date"] ) & ( data["date"] <= period_end )

if data[is_in_period].empty:
    top_product= (
        data
        .groupby("productId")["quantity"]
        .sum()
        .idxmax()
    )
    top_category= (
    data
    .groupby("category")["quantity"]
    .sum()
    .idxmax()
)
else:     
    top_product= (
        data[is_in_period]
        .groupby("productId")["quantity"]
        .sum()
        .idxmax()
    )
    top_category= (
    data[is_in_period]
    .groupby("category")["quantity"]
    .sum()
    .idxmax()
)
product_list = list( data["productId"].unique() )
top_product_index = product_list.index(top_product)

category_list = list( data["category"].unique() )
top_category_index = category_list.index(top_category)

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


if data.empty:
    print('Dataset vacío')


# -----------------------------------------------------------
# LOGO Y TITULO
# -----------------------------------------------------------

col1, col2 = st.columns([1, 8])
with col1:
    st.image("assets/logo.png", width=50)

with col2:
    st.markdown("### Inventario CT International")



tab1, tab2 = st.tabs(["Ventas","Inventario"])

# ===========================================================
#                       ANÁLISIS VENTAS
# ===========================================================

with tab1:
    left, right = st.columns([1.3, 3.7])

    with left:

        
# -----------------------------------------------------------
# INFO DE PRODUCTO/CATEGORIA
# -----------------------------------------------------------
        st.markdown('**Filtros**')
        col1, col2 = st.columns(2)
        with col1 :
            analysis_lvl = pick_main_element(label='Nivel de análisis',options=["Productos","Categorías"],default='Productos',key='Nivel de análisis seleccionado')
        with col2 :
            outliers= pick_main_element(label='Análisis con ventas anomalas incluídas',options= ['Sí','No'],default='Sí',key='Incluir ventas anómalas')
        
        
        branch = st.selectbox("Sucursal", branch_list, index=frequent_branch_index)


        if outliers=='Sí':
            include_outliers = True
        else: 
            include_outliers = False

        if analysis_lvl=="Productos":
                categories = []
                products = pick_elements(label="Producto(s)",options=product_list,default=[top_product],key="Sucursal Productos Seleccionados")
        
        if analysis_lvl=="Categorías":
                products = []
                categories = pick_elements(label="Categoría(s)",options=category_list,default=[top_category],key="Sucursal Categorías Seleccionadas")
                
        col1,col2 = st.columns(2)
        with col1:

            if analysis_lvl=="Productos":
                main_element = pick_main_element(label="Producto de análisis",options= products,key="producto de análisis",default=top_product)
                element_title= f"**producto:** {main_element}"

            if analysis_lvl=="Categorías":
                main_element = pick_main_element(label="Categoría de análisis",options= categories,key="categoría de análisis",default=top_category)
                element_title = f"**categoría:** {main_element}"
                

        with col2:
            st.markdown("Periodo")
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

        st.markdown(f'**Información de** {element_title}')
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
                        str(main_element),
                        str(category),
                        str(cost_per_unit),
                        str(price_range[1]),
                        str(clients_str)
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
                                    outliers = include_outliers,
                                    start_date=period_start,end_date=period_end)
        global_period_sales_fig = period_sales(data=data,
                                    selected_elements=selected_elements,
                                    element_column=element_column,
                                    outliers = include_outliers,
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
                          outliers = include_outliers,
                          start_date=period_start,end_date=period_end)

                st.markdown(f"**{branch}**")
                st.pyplot(branch_histogram)

        with c2:
                global_histogram = sales_hist(data=data,
                          main_element=main_element,
                          element_column=element_column,
                          outliers = include_outliers,
                          start_date=period_start,end_date=period_end)

                st.markdown("**Global**")
                st.pyplot(global_histogram)
                
                


# -----------------------------------------------------------
# KPIs (VENTAS)
# -----------------------------------------------------------
        filtered = data[is_element & in_branch].copy()
        filtered_current = filtered[is_in_period].copy()
        if filtered_current.empty:
            st.warning("No hay datos para el elemento seleccionado en este periodo.")
            st.stop()

        total_branch_sales = round ( filtered_current["quantity"].sum() ,2 )
        total_branch_cost = round ( filtered_current["cost"].sum() ,2 )
        total_branch_profit = round( filtered_current["income"].sum() - total_branch_cost ,2 )
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

        sales_color = "#0cb91a" if sales_rate >= 0 else "#ef4444" 
        profit_color = "#0cb91a" if profit_rate >= 0 else "#ef4444" 
        cost_color = "#0cb91a" if cost_rate >= 0 else "#ef4444" 

        with col1:
            st.markdown(
                f'''
                <div class="kpi-title">
                    <h3>Unidades Vendidas</h3>
                    <h2>{total_branch_sales:,}</h2>
                    <p style="color: {sales_color}; font-weight: 600;">
                    {sales_rate:+.1f}%</p>
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
                    <p style="color: {profit_color}; font-weight: 600;">
                    {profit_rate:+.1f}% </p>
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
                    <p style="color: {cost_color}; font-weight: 600;">
                    {cost_rate:+.1f}%</p>
                </div>
                ''',
                unsafe_allow_html=True
            )

        global_filtered = global_data [is_global_element].copy()
        global_filtered_current = global_filtered[is_in_period]
        if global_filtered.empty:
            st.warning("No hay datos para el elemento seleccionado en este periodo.")
            st.stop()

        total_sales = round( global_filtered["quantity"].sum() , 2 )
        total_cost = round( global_filtered["cost"].sum() , 2 )
        total_profit = round( global_filtered["income"].sum() - total_cost ,2 )
        

        col1, col2, col3 = st.columns(3)
        previous_period = ( pd.to_datetime(period_start)-datetime.timedelta(days=30) <= global_filtered['date'] ) & ( global_filtered['date'] <= pd.to_datetime(period_start) ) 
        global_filtered_prev = global_filtered[previous_period]
       
        global_prev_sales = global_filtered_prev["quantity"].sum()
        global_prev_cost = global_filtered_prev["cost"].sum()
        global_prev_profit = global_filtered_prev["income"].sum() - global_prev_cost


        global_sales_rate = growth_rate(total_sales, global_prev_sales)
        global_profit_rate = growth_rate(total_profit, global_prev_profit)
        global_cost_rate = growth_rate(total_cost, global_prev_cost)
        global_sales_color = "#0cb91a" if global_sales_rate >= 0 else "#ef4444" 
        global_profit_color = "#0cb91a" if global_profit_rate >= 0 else "#ef4444" 
        global_cost_color = "#0cb91a" if global_cost_rate >= 0 else "#ef4444"
        with col1:
            st.markdown(f'''
                        <div class="kpi-title">
                            <h3>Unidades Vendidas</h3>
                            <h2>{total_sales:,} </h2>
                            <p style="color: {global_sales_color}; font-weight: 600;">
                            {global_sales_rate:+.1f}%</p>
                        </div>
                        ''', 
                        unsafe_allow_html=True)
        with col2:
            st.markdown(f'''
                        <div class="kpi-title">
                            <h3>Ganancia Total (MXN)</h3>
                            <h2>${total_profit:,} </h2>
                            <p style="color: {global_profit_color}; font-weight: 600;">
                            {global_profit_rate:+.1f}%</p>
                        </div>
                        ''',
                        unsafe_allow_html=True)
        with col3:
            st.markdown(f'''
                        <div class="kpi-title">
                            <h3>Costo Total (MXN)</h3>
                            <h2>${total_cost:,}</h2>
                            <p style="color: {global_cost_color}; font-weight: 600;">
                            {global_cost_rate:+.1f}%</p>
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
                merged = cached_prepare_sales_heatmap_data(
                                                    data=global_data,
                                                    main_element=main_element,
                                                    element_column=element_column,
                                                    start_date=period_start,
                                                    end_date=period_end,
                                                    outliers = include_outliers,
                                                )

                map_obj, selected_state = render_sales_heat_map(merged, 
                                                                main_element,
                                                                map_key="Ventas Mapa")
        with col2:
            if analysis_lvl=="Productos":
                st.pyplot(product_priorities)
            if analysis_lvl=="Categorías":
                st.pyplot(category_priorities)
            
        




# ===========================================================
#                       ANÁLISIS INVENTARIO
# ===========================================================


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
                    str(main_element),
                    str(category),
                    str(cost_per_unit),
                    str(price_range[1]),
                    str(clients_str)
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
# INVENTARIO
# -----------------------------------------------------------
        
        branch_period_inventory_fig = period_inventory(data=inventory,
                                    branch_storage=branch_storage,
                                    selected_elements=selected_elements,
                                    element_column=element_column,
                                    branch=branch,
                                    start_date=period_start_global,end_date=period_end_global)

        global_period_inventory_fig = period_inventory(data=inventory,
                                    branch_storage=branch_storage,
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
                          outliers=include_outliers,
                          start_date=period_start_global,end_date=period_end_global)

                st.markdown(f"**{branch}**")
                st.pyplot(branch_histogram)

        with col2:
                global_histogram = sales_hist(data=data,
                          main_element=main_element,
                          element_column=element_column,
                          outliers=include_outliers,
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
                merged = cached_prepare_sales_heatmap_data(
                                                    data=global_data,
                                                    main_element=main_element,
                                                    element_column=element_column,
                                                    start_date=period_start_global,
                                                    end_date=period_end_global,
                                                    outliers=include_outliers,
                                                )

                map_obj, selected_state = render_sales_heat_map(merged, 
                                                                main_element,
                                                                map_key="Global Mapa")
        with col2:
            if analysis_lvl=="Productos":
                st.pyplot(product_priorities)
            if analysis_lvl=="Categorías":
                st.pyplot(category_priorities)



