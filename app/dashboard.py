import streamlit as st
import pandas as pd
import datetime

from functools import wraps
from typing import List,Callable,Tuple,Dict
from dashboard.utils import top_n,add_states_column,identify_outlier_sales,calculate_top_product_and_category,calculate_frequent_branch,growth_rate
from dashboard.graphs import *
from dashboard.data import load_data
from dashboard.filters import include_outliers_filter,analysis_lvl_filter,products_filter,categories_filter,branch_filter,main_element_filter,period_filter


def load_css(file_name):

    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

def make_cached(func:Callable):
    """Crea versiones cacheadas de funciones"""
    @st.cache_data(ttl=3600*12,show_spinner=False)
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper


def left_section(data:pd.DataFrame,
                 period_start:Date,
                 period_end:Date,
                 branch_list:List[str],
                 product_list:List[str],
                 category_list:List[str],
                 top_product:str,
                 top_category:str,
                 frequent_branch_index:int,
                 tab:str)->Tuple[str,str,bool,str,str,str,str,List,str]:

    def filters(tab:str)->Tuple[str,str,bool,List,List]:
        st.markdown('**Filtros**')
        col1, col2 = st.columns(2)
        with col1 :
            analysis_lvl = analysis_lvl_filter(tab)
        with col2 :
            include_outliers = include_outliers_filter(tab) 
                       
        branch = branch_filter(branch_list,frequent_branch_index,tab)
        
        categories = categories_filter(category_list,top_category,analysis_lvl,tab)   
        products = products_filter(product_list,top_product,analysis_lvl,tab)

        return analysis_lvl,branch,include_outliers,categories,products
    
    def analysis_element_and_period_select(analysis_lvl:str,element_list:list[str],top_element:str,start_date:datetime.date,end_date:datetime.date,tab:str):
        col1,col2 = st.columns(2)
        with col1:
            if analysis_lvl=="Productos":
                main_element,element_title = main_element_filter(analysis_lvl,element_list,top_element,tab)
        with col2:
            st.markdown('Periodo')
            period_start,period_end = period_filter(start_date,end_date,tab)
            
        return main_element,element_title,period_start,period_end

    def element_selection(analysis_lvl,
                          products,
                          categories):
        elements={"Productos":products,
                  "Categorías":categories}[analysis_lvl]
        
        column={"Productos":"productId",
                "Categorías":"category"}[analysis_lvl]
        return elements,column
    
    def element_info(data:pd.DataFrame,
                     selected_element:str,
                     element_column:str,):
        
        is_element = data[element_column]== selected_element
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


    analysis_lvl,branch,include_outliers,categories,products = filters(tab)
    if len(products)==0:
        element_list = categories
        top_element = top_category
    else:
        element_list = products
        top_element = top_product

    main_element,element_title,period_start,period_end = analysis_element_and_period_select(analysis_lvl= analysis_lvl,
                                                                                            element_list= element_list,
                                                                                            top_element = top_element,
                                                                                            start_date  = period_start,
                                                                                            end_date    = period_end,
                                                                                            tab         = tab
                                                                                            )
 
    selected_elements,element_column = element_selection(analysis_lvl=analysis_lvl,
                                                         products=products,
                                                         categories=categories)

    
    element_info(data=data,
                 selected_element=main_element,
                 element_column=element_column)

        
        
    return analysis_lvl,branch,include_outliers,main_element,element_title,period_start,period_end,selected_elements,element_column

def right_section(data:pd.DataFrame,
                  global_data:pd.DataFrame,
                  cached_functions:Dict[str,Callable],
                  main_element:str,
                  selected_elements:List,
                  element_column:str,
                  branch:str,
                  include_outliers :bool,
                  period_start,period_end,
                  analysis_lvl:str,
                  tab:str,
                  branch_storage:Dict=None):
    
    def sales_plots(data:pd.DataFrame,
                    selected_elements:List,
                    element_column:str,
                    branch:str,
                    include_outliers :bool,
                    period_start,period_end):

        branch_period_sales_fig = period_sales(data=data,
                                        selected_elements=selected_elements,
                                        element_column=element_column,
                                        branch=branch,
                                        include_outliers = include_outliers,
                                        start_date=period_start,end_date=period_end)
        global_period_sales_fig = period_sales(data=data,
                                        selected_elements=selected_elements,
                                        element_column=element_column,
                                        include_outliers = include_outliers,
                                        start_date=period_start,end_date=period_end)

            
        st.markdown("### Ventas Diarias")
            
        col1, col2 = st.columns(2)
        with col1:
            st.pyplot(branch_period_sales_fig)
        with col2:
            st.pyplot(global_period_sales_fig)

    def inventory_plots(inventory:pd.DataFrame,
                        branch_storage:Dict,
                        selected_elements:List,
                        element_column:str,
                        branch:str,
                        period_start,
                        period_end):   
                 
            branch_period_inventory_fig = period_inventory(data=inventory,
                                        branch_storage=branch_storage,
                                        selected_elements=selected_elements,
                                        element_column=element_column,
                                        branch=branch,
                                        start_date=period_start,end_date=period_end)

            global_period_inventory_fig = period_inventory(data=inventory,
                                        branch_storage=branch_storage,
                                        selected_elements=selected_elements,
                                        element_column=element_column,
                                        start_date=period_start,end_date=period_end)
            
            st.markdown("### Existencia Diaria")
            col1, col2 = st.columns(2)
            with col1:
                st.pyplot(branch_period_inventory_fig)
            with col2:
                st.pyplot(global_period_inventory_fig) 

    def histogram_plots(data:pd.DataFrame,
                        element_column:str,
                        branch:str,
                        include_outliers :bool,
                        period_start,period_end):
        c1, c2 = st.columns(2)

        with c1:
                branch_histogram = sales_hist(data=data,
                            main_element=main_element,
                            element_column=element_column,
                            branch=branch,
                            include_outliers = include_outliers,
                            start_date=period_start,end_date=period_end)

                st.markdown(f"**{branch}**")
                st.pyplot(branch_histogram)

        with c2:
                global_histogram = sales_hist(data=data,
                            main_element=main_element,
                            element_column=element_column,
                            include_outliers = include_outliers,
                            start_date=period_start,end_date=period_end)

                st.markdown("**Global**")
                st.pyplot(global_histogram)
    
    def sales_kpis(data:pd.DataFrame)->tuple[int,float,float]:
        df = data.copy()
        total_sales = df['quantity'].sum() 
        total_cost = round ( df['cost'].sum() ,2 )
        total_profit = round( df['income'].sum() - total_cost ,2 )
        return total_sales,total_cost,total_profit
    
    def inventory_kpis(data:pd.DataFrame)->tuple[int,int]:
        df = data.copy()
        latest_register=df['date']==df['date'].max()
        current_stock = int((df[latest_register]["stock"].sum()))
        branches = list(df.branch.unique())
        supplied_stock = 0
        for b in branches:
            df_filtered = df[df['branch']==b]
            df_filtered['difference'] = (
                                        df_filtered.groupby("date")["stock"]
                                        .transform("sum")
                                        .diff()
                                        .fillna(0)
                                    )
            positive_supply = df_filtered['difference']>0
            supplied_stock += int(df_filtered[positive_supply]['difference'].sum())
       
        return current_stock,supplied_stock
    
    def kpi_display(data:pd.DataFrame,
                    selected_element:str,
                    element_column:str,
                    period_start,
                    include_outliers:bool|None,
                    tab:str,
                    branch:str=None):
        
        df = data.copy()
        period_start = period_start
        current_period = (period_start,period_start+datetime.timedelta(days=30))
        previous_period = (period_start -datetime.timedelta(days=30),period_start)

        current_filters = GraphFilters(config= GraphFilterConfig(start_date=current_period[0],
                                                     end_date=current_period[1],
                                                     element_column=element_column,
                                                     selected_elements=[selected_element],
                                                     branch=branch,
                                                     include_outliers=include_outliers))
        
        previous_filters = GraphFilters(config= GraphFilterConfig(start_date=previous_period[0],
                                                     end_date=previous_period[1],
                                                     element_column=element_column,
                                                     selected_elements=[selected_element],
                                                     branch=branch,
                                                     include_outliers=include_outliers))

        filtered_current = current_filters.apply(df)
        filtered_prev = previous_filters.apply(df)
        

        if filtered_current.empty:
                st.warning("No hay datos para el elemento seleccionado en este periodo.")
                return None
        if filtered_prev.empty:
                st.warning("No hay datos del periodo previo para el elemento seleccionado en este periodo.")
                return None
        if branch:
            title = 'Sucursal'
        else :
            title = 'Global'
        if tab=='ventas':
            current_sales,current_cost,current_profit = sales_kpis(data=filtered_current)
            prev_sales,prev_cost,prev_profit = sales_kpis(data=filtered_prev)
            
            sales_rate = growth_rate(current_sales, prev_sales)
            profit_rate = growth_rate(current_profit, prev_profit)
            cost_rate = growth_rate(current_cost, prev_cost)

            sales_color = "#0cb91a" if sales_rate >= 0 else "#ef4444" 
            profit_color = "#0cb91a" if profit_rate >= 0 else "#ef4444" 
            cost_color = "#0cb91a" if cost_rate >= 0 else "#ef4444" 

            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(
                        f'''
                        <div class="kpi-title">
                            <h3>Ventas {title} </h3>
                            <h2>{current_sales:,}</h2>
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
                            <h3>Ganancia {title}</h3>
                            <h2>${current_profit:,}</h2>
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
                            <h3>Costo {title}</h3>
                            <h2>${current_cost:,}</h2>
                            <p style="color: {cost_color}; font-weight: 600;">
                            {cost_rate:+.1f}%</p>
                        </div>
                        ''',
                        unsafe_allow_html=True
                    )
        if tab=='inventario':
            current_stock,current_supplied= inventory_kpis(data=filtered_current)
            prev_stock,prev_supplied = inventory_kpis(data=filtered_prev)
            
            stock_rate = growth_rate(current_stock, prev_stock)
            supply_rate = growth_rate(current_supplied, prev_supplied)
            

            stock_color = "#0cb91a" if stock_rate >= 0 else "#ef4444" 
            supply_color = "#0cb91a" if supply_rate >= 0 else "#ef4444" 
             

            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(
                        f'''
                        <div class="kpi-title">
                            <h3>Existencia {title}</h3>
                            <h2>{current_stock:,}</h2>
                            <p style="color: {stock_color}; font-weight: 600;">
                            {stock_rate:+.1f}%</p>
                        </div>
                        ''',
                        unsafe_allow_html=True
                    )

            with col2:
                st.markdown(
                        f'''
                        <div class="kpi-title">
                            <h3>Compras {title}</h3>
                            <h2>{current_supplied:,}</h2>
                            <p style="color: {supply_color}; font-weight: 600;">
                            {supply_rate:+.1f}% </p>
                        </div>
                        ''',
                        unsafe_allow_html=True
                    )

    def priority_and_map_plots(global_data:pd.DataFrame|None,
                               inventory:pd.DataFrame|None,
                               main_element:str,
                               element_column:str,
                               period_start,
                               period_end,
                               include_outliers:bool|None,
                               branch:str,
                               analysis_lvl:str,
                               tab:str):  
        if tab=='ventas':
            sales_priorities = abc_bar_chart(data=global_data,
                                             element_column=element_column,
                                             branch=branch,
                                             include_outliers=include_outliers,
                                             start_date=period_start,
                                             end_date=period_end)

            col1, col2 = st.columns(2)
            with col1:
                    st.markdown(f"**Mapa de {tab}**")
                    merged = cached_functions['prepare_sales_heatmap_data'](
                                                            data=global_data,
                                                            main_element=main_element,
                                                            element_column=element_column,
                                                            start_date=period_start,
                                                            end_date=period_end,
                                                            include_outliers = include_outliers,
                                                            tab= tab
                                                        )
                    map_obj = render_sales_heat_map(merged=merged, 
                                                    main_element=main_element,
                                                    tab=tab,
                                                    map_key=f"{tab} Mapa")
                    if isinstance(map_obj,Figure):
                        st.pyplot(map_obj)
            
            with col2:
                st.markdown(f"**Prioridades de {analysis_lvl}**")
                st.pyplot(sales_priorities)

        if tab=='inventario':
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Mapa de {tab}**")
                merged = cached_functions['prepare_sales_heatmap_data'](
                                                                        data=inventory,
                                                                        main_element=main_element,
                                                                        element_column=element_column,
                                                                        start_date=period_start,
                                                                        end_date=period_end,
                                                                        include_outliers = include_outliers,
                                                                        tab= tab
                                                                    )
        
                map_obj= render_sales_heat_map(merged=merged, 
                                               main_element=main_element,
                                               tab=tab,
                                               map_key=f"{tab} Mapa")

    if tab=='ventas':
        sales_plots(data,
                    selected_elements,
                    element_column,
                    branch,
                    include_outliers,
                    period_start,period_end
                    )
        histogram_plots(data=data,
                    element_column=element_column,
                    branch=branch,
                    include_outliers=include_outliers,
                    period_start=period_start,
                    period_end=period_end
                    )
        # KPIs de Sucursal
        kpi_display(data=data,
                    selected_element=main_element,
                    element_column=element_column,
                    period_start=period_start,
                    include_outliers=include_outliers,
                    branch=branch,
                    tab=tab
                    )
        # KPIs Globales
        kpi_display(data=global_data,
                    selected_element=main_element,
                    element_column=element_column,
                    period_start=period_start,
                    include_outliers=include_outliers,
                    tab=tab
                    )
        priority_and_map_plots(global_data=global_data,
                                inventory=None,
                                main_element=main_element,
                                element_column=element_column,
                                period_start=period_start,
                                period_end=period_end,
                                include_outliers=include_outliers,
                                branch=branch,
                                analysis_lvl=analysis_lvl,
                                tab=tab) 

    if tab=='inventario':
        inventory_plots(inventory=data,
                        branch_storage=branch_storage,
                        selected_elements=selected_elements,
                        element_column=element_column,
                        branch=branch,
                        period_start=period_start,
                        period_end=period_end)
        

        # KPIs de Sucursal
        kpi_display(data=data,
                    selected_element=main_element,
                    element_column=element_column,
                    period_start=period_start,
                    include_outliers=None,
                    branch=branch,
                    tab=tab
                    )
        # KPIs Globales
        kpi_display(data=data,
                    selected_element=main_element,
                    element_column=element_column,
                    period_start=period_start,
                    include_outliers=None,
                    tab=tab
                    )
        priority_and_map_plots( global_data=None,
                                inventory=data,
                                main_element=main_element,
                                element_column=element_column,
                                period_start=period_start,
                                period_end=period_end,
                                branch=branch,
                                include_outliers=None,
                                analysis_lvl=analysis_lvl,
                                tab=tab)   
                     



# ===========================================================
#                       MAIN
# ===========================================================


def main():
    st.set_page_config(
        page_title="CT Dashboard",
        page_icon="assets/logo.png",
        layout="wide",  
        initial_sidebar_state="collapsed" 
    )

    load_css("assets/styles.css")

    funcs = [load_data,
            identify_outlier_sales,
            prepare_sales_heatmap_data
            ]

    cache_wrappers ={}
    for f in funcs:
        cache_wrappers[f.__name__]= make_cached(f)


# ===========================================================
#                       LOGO Y TITULO
# ===========================================================

    col1, col2 = st.columns([1, 8])
    with col1:
        st.image("assets/logo.png", width=50)

    with col2:
        st.markdown("### Dashboard CT International")
           
        


    sales, stock = st.tabs(["Ventas","Inventario"])


# ===========================================================
#                       VALORES PREDETERMINADOS
# ===========================================================
    with st.spinner("Cargando valores predeterminados..."):
        today = datetime.date.today() 
        if today.day < 15:
            period_start =  datetime.date(today.year, today.month -1 , 15) 
            period_end = today 
        else:
            period_start = datetime.date(today.year, today.month, 1) 
            period_end =  today 

        with st.spinner("Cargando datos..."):
            branch_storage = load_data("SELECT * FROM raw.almacenes")
            inventory = load_data("""SELECT inv.*,
                                            alm.branch,
                                            ca.category
                                     FROM etl.inventory AS inv
                                     JOIN raw.almacenes AS alm ON inv."storageId"=alm."storageId"
                                     JOIN raw.productos AS prod ON inv."productId"=prod."productId"
                                     LEFT JOIN raw.categorias as ca ON CAST(prod."categoryId" AS numeric)::integer=ca."categoryId"
                                     WHERE prod."categoryId"<>'unknown'   
                                  """)
            inventory = add_states_column(inventory)

            
            data_query = f"""SELECT v."productId",
                                    v.quantity,
                                    v.date,
                                    v.price,
                                    v.total,
                                    v."clientId",
                                    v.folio,
                                    v.description,
                                    v.cost,
                                    v."storageId",
                                    v."branchId",
                                    v.branch,
                                    c.category
                             FROM marts.ventas AS v
                             LEFT JOIN raw.categorias as c ON CAST(v."categoryId" AS numeric)::integer=c."categoryId"
                             WHERE v."categoryId"<>'unknown'
                             AND v.date BETWEEN '{period_start}' AND '{period_end}' """
            global_data = load_data(data_query)
            global_data = add_states_column(global_data)
            global_data = global_data.astype(dtype={"date":"date32[pyarrow]"})
            global_data['income'] = global_data['price'] * global_data['quantity']
            global_data = cache_wrappers['identify_outlier_sales'](global_data,element_column='productId')


            data = global_data.copy()
                
        # Producto con cantidad de unidades más vendidas dentro de periodo
        top_product,top_category = calculate_top_product_and_category(data=data,
                                                                    period_start=period_start,
                                                                    period_end=period_end)

        product_list = list( data["productId"].unique() )
        category_list = list( data["category"].unique() )
        branch_list = list( data["branch"].unique() )


        # Sucursal en donde se vende más seguido el producto más vendido
        frequent_branch = calculate_frequent_branch(data=data,
                                                    top_product=top_product)
        frequent_branch_index = branch_list.index(frequent_branch)

        if data.empty:
            print('Dataset vacío')


# ===========================================================
#                       ANÁLISIS VENTAS
# ===========================================================

    with sales:
        left, right = st.columns([1.3, 3.7])

        with left:
            analysis_lvl,branch,include_outliers,main_element,element_title,period_start,period_end,selected_elements,element_column = left_section(data=data,
                                                                                                                                                    period_start=period_start,
                                                                                                                                                    period_end=period_end,
                                                                                                                                                    branch_list=branch_list,
                                                                                                                                                    product_list=product_list,
                                                                                                                                                    category_list=category_list,
                                                                                                                                                    top_product=top_product,
                                                                                                                                                    top_category=top_category,
                                                                                                                                                    frequent_branch_index=frequent_branch_index,
                                                                                                                                                    tab='ventas')        
        
        with right:
            right_section(data=data,
                          global_data=global_data,
                          main_element=main_element,
                          cached_functions=cache_wrappers,
                          selected_elements=selected_elements,
                          element_column=element_column,
                          branch=branch,
                          include_outliers =include_outliers,
                          period_start=period_start,
                          period_end=period_end,
                          analysis_lvl=analysis_lvl,
                          tab='ventas')

        

# ===========================================================
#                       ANÁLISIS INVENTARIO
# ===========================================================


    with stock:

        left, right = st.columns([1.2, 3])

    with left:

        inv_analysis_lvl,inv_branch,_,inv_main_element,element_title,inv_period_start,inv_period_end,inv_selected_elements,inv_element_column = left_section(    data=data,
                                                                                                                                                                 period_start=period_start,
                                                                                                                                                                 period_end=period_end,
                                                                                                                                                                 branch_list=branch_list,
                                                                                                                                                                 product_list=product_list,
                                                                                                                                                                 category_list=category_list,
                                                                                                                                                                 top_product=top_product,
                                                                                                                                                                 top_category=top_category,
                                                                                                                                                                 frequent_branch_index=frequent_branch_index,
                                                                                                                                                                 tab='inventario')

    with right:
        right_section(  data=inventory,
                        branch_storage=branch_storage,
                        global_data=global_data,
                        cached_functions=cache_wrappers,
                        main_element=inv_main_element,
                        selected_elements=inv_selected_elements,
                        element_column=inv_element_column,
                        branch=inv_branch,
                        include_outliers =include_outliers,
                        period_start=inv_period_start,
                        period_end=inv_period_end,
                        analysis_lvl=inv_analysis_lvl,
                        tab='inventario')



if __name__ == "__main__":
    main()