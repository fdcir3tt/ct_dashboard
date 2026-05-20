import streamlit as st
import pandas as pd
import datetime

from functools import wraps
from typing import List,Callable,Tuple,Dict
from dashboard.utils import add_states_column,identify_outlier_sales,calculate_top_product_and_category,calculate_frequent_branch
from dashboard.graphs import *
from dashboard.plot_displays import sales_plots,inventory_plots,display_element_info,kpi_display,histogram_plots,priority_and_map_plots,kpi_calculator
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

@st.cache_data(ttl=300,show_spinner=False)
def load_sales_data(start_date:datetime.date,end_date:datetime.date)->dict[str,pd.DataFrame]:
    
    data_query =  """SELECT product_id,
                                quantity,
                                date,
                                price,
                                total,
                                client_id,
                                folio,
                                description,
                                cost,
                                sale_storage_id,
                                branch_id,
                                branch,
                                category 
                         FROM marts.informacion_ventas
                         WHERE date BETWEEN %s AND %s"""
              
    global_data = load_data(data_query,params=(start_date,end_date))
    global_data = add_states_column(global_data)
    global_data = global_data.astype(dtype={"date":"date32[pyarrow]"})
    global_data['income'] = global_data['price'] * global_data['quantity']
    global_data = identify_outlier_sales(global_data,element_column='product_id')


    data = global_data.copy()

    return {"global_data":global_data,"data":data}

@st.cache_data(ttl=300,show_spinner=False)
def load_inventory_data(start_date:datetime.date,end_date:datetime.date)->dict[str,pd.DataFrame]:
    
    
    branch_storage = load_data("SELECT * FROM raw.catalogo_almacenes")
    query = """SELECT product_id,
                          date,
                          stock,
                          storage_id,
                          branch,
                          category 
                   FROM marts.informacion_inventario
                   WHERE date BETWEEN %s AND %s"""
        
    inventory = load_data(query,params=(start_date,end_date))
    inventory = add_states_column(inventory)

    return {"branch_storage":branch_storage,"inventory":inventory}

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
        
        column={"Productos":"product_id",
                "Categorías":"category"}[analysis_lvl]
        return elements,column
    
    
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

    
    display_element_info(data=data,
                         element_title=element_title,
                         analysis_lvl=analysis_lvl,
                         selected_element=main_element,
                         element_column=element_column)

        
        
    return analysis_lvl,branch,include_outliers,main_element,element_title,period_start,period_end,selected_elements,element_column

def right_section(data:pd.DataFrame,
                  global_data:pd.DataFrame,
                  main_element:str,
                  selected_elements:List,
                  element_column:str,
                  branch:str,
                  include_outliers :bool,
                  period_start,period_end,
                  analysis_lvl:str,
                  tab:str,
                  branch_storage:Dict=None):
    
            
    if tab=='ventas':
        st.markdown("### Ventas Diarias")
        sales_plots(data,
                    selected_elements,
                    element_column,
                    branch,
                    include_outliers,
                    period_start,period_end)    
        

        histogram_plots(data=data,
                    element_column=element_column,
                    main_element=str,
                    branch=branch,
                    include_outliers=include_outliers,
                    period_start=period_start,
                    period_end=period_end
                    )
        
        # KPIs de Sucursal
        branch_sales_rates = kpi_calculator(data= data,
                                            selected_element= main_element,
                                            element_column= element_column,
                                            period_start= period_start,
                                            include_outliers= include_outliers,
                                            branch= branch,
                                            tab= tab)
        
            
        kpi_display(branch_sales_rates,tab,'Sucursal')
        
        # KPIs Globales
        global_sales_rates = kpi_calculator(data= global_data,
                                            selected_element= main_element,
                                            element_column= element_column,
                                            period_start= period_start,
                                            include_outliers= include_outliers,
                                            tab= tab )
        kpi_display(global_sales_rates,tab,'Global')
        
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
        st.markdown("### Existencia Diaria")
        inventory_plots(inventory=data,
                       branch_storage=branch_storage,
                       selected_elements=selected_elements,
                       element_column=element_column,
                       branch=branch,
                       period_start=period_start,
                       period_end=period_end)

        # KPIs de Sucursal
        branch_inventory_rates = kpi_calculator(data=data,
                                                selected_element=main_element,
                                                element_column=element_column,
                                                period_start=period_start,
                                                include_outliers=None,
                                                branch=branch,
                                                tab=tab
                                                )
            
        kpi_display(branch_inventory_rates,tab,'Sucursal')
        # KPIs Globales
        global_inventory_rate = kpi_calculator(data=data,
                                               selected_element=main_element,
                                               element_column=element_column,
                                               period_start=period_start,
                                               include_outliers=None,
                                               tab=tab)
        kpi_display(global_inventory_rate,tab,'Global')

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
                     
def load_dates(tab:str)->tuple[date,date]:
    today = datetime.date.today() 
    start_date = st.session_state.get(f"Sucursal Inicio {tab}")
    end_date = st.session_state.get(f"Sucursal Fin {tab}")

    if start_date is None:
        if today.day < 15:
            period_start =  datetime.date(today.year, today.month -1 , 15) 
        else:
            period_start = datetime.date(today.year, today.month, 1)
    else:
        period_start = start_date

    if end_date is None:
        period_end = today 
    else:
        period_end = end_date

    return period_start,period_end



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

    funcs = [load_sales_data,
             load_inventory_data,
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
    
                

# ===========================================================
#                       ANÁLISIS VENTAS
# ===========================================================

    with sales:
        left, right = st.columns([1.3, 3.7])

        with left:
            period_start,period_end = load_dates(tab="ventas")
            with st.spinner("Cargando datos de ventas..."):
                sales_data_dict = load_sales_data(period_start,period_end)
            data = sales_data_dict["data"]
            global_data = sales_data_dict["global_data"]
            
            with st.spinner("Cargando valores predeterminados..."):
                # Producto con cantidad de unidades más vendidas dentro de periodo
                
                top_product,top_category = calculate_top_product_and_category(data=data,
                                                                            period_start=period_start,
                                                                            period_end=period_end)

                product_list = list( data["product_id"].unique() )
                category_list = list( data["category"].unique() )
                branch_list = list( data["branch"].unique() )


                # Sucursal en donde se vende más seguido el producto más vendido
                frequent_branch = calculate_frequent_branch(data=data,
                                                            top_product=top_product)
                frequent_branch_index = branch_list.index(frequent_branch)

                if data.empty:
                    print('Dataset vacío')

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
        
        inv_period_start,inv_period_end = load_dates(tab='inventario')
        with st.spinner("Cargando datos de inventario..."):
            inv_data_dict = load_inventory_data(inv_period_start,inv_period_end)
        inventory = inv_data_dict["inventory"]
        branch_storage = inv_data_dict["branch_storage"]
        
        inv_analysis_lvl,inv_branch,_,inv_main_element,element_title,inv_period_start,inv_period_end,inv_selected_elements,inv_element_column = left_section(    data=data,
                                                                                                                                                                 period_start=inv_period_start,
                                                                                                                                                                 period_end=inv_period_end,
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