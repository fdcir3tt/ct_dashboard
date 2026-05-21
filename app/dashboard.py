import streamlit as st
import pandas as pd
import datetime

from dashboard.utils import add_states_column,identify_outlier_sales,calculate_top_product_and_category,calculate_frequent_branch
from dashboard.plot_displays import sales_plots,inventory_plots,display_element_info,kpi_display,histogram_plots,priority_and_map_plots,kpi_calculator
from dashboard.data import load_data
from dashboard.filters import include_outliers_filter,analysis_lvl_filter,products_filter,categories_filter,branch_filter,main_element_filter,period_filter
from dashboard.streamlit_utils import fetch_selected_elements,fetch_analysis_lvl,fetch_dates,fetch_main_element,fetch_branch,fetch_include_outliers

def load_css(file_name):

    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def filters(option_lists:dict[str,list[str]],default_values:dict[str,str],tab:str):
    branch_list   = option_lists["branches"]
    category_list = option_lists["categories"]
    product_list  = option_lists["products"]

    default_branch      = default_values["branch"]
    default_product     = default_values["product"]
    default_category    = default_values["category"]
    start_date,end_date = load_dates(tab)

    st.markdown('**Filtros**')
    col1, col2 = st.columns(2)
    with col1 :
        analysis_lvl = analysis_lvl_filter(tab)
    with col2 :
        include_outliers_filter(tab) 
    
    default_branch_index = ( branch_list.index(default_branch) if default_branch in branch_list else 0 )

    branch_filter(branch_list,default_branch_index,tab)
    categories = categories_filter(category_list,default_category,analysis_lvl,tab)   
    products = products_filter(product_list,default_product,analysis_lvl,tab)
    products = products or []

    if len(products)==0:
        element_list = categories
        default_element = default_category
    else:
        element_list = products
        default_element = default_product

    col3,col4 = st.columns(2)
    with col3:
            
        main_element_filter(analysis_lvl,element_list,default_element,tab)
    with col4:
        st.markdown('Periodo')
        period_filter(start_date,end_date,tab)




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
def load_inventory_data(start_date:datetime.date,end_date:datetime.date,element_column:str,elements_selected:list[str])->dict[str,pd.DataFrame]:
    placeholders = ",".join(["%s"] * len(elements_selected))
    
    branch_storage = load_data("SELECT * FROM raw.catalogo_almacenes")
    if not elements_selected:
        return {"branch_storage": branch_storage,
                "inventory": pd.DataFrame()}
    query = f"""SELECT product_id,
                          date,
                          stock,
                          storage_id,
                          branch,
                          category 
                   FROM marts.informacion_inventario
                   WHERE date BETWEEN %s AND %s
                   AND {element_column} IN ({placeholders}) """
    
    inventory = load_data(query,params=(start_date,end_date,*elements_selected))
    inventory = add_states_column(inventory)

    return {"branch_storage":branch_storage,"inventory":inventory}



def left_section(data:pd.DataFrame,
                 option_lists:dict[str,list[str]],
                 default_values:dict[str,str],
                 tab:str):

    filters(option_lists,default_values,tab)
    analysis_lvl = fetch_analysis_lvl(tab)
    main_element = fetch_main_element(analysis_lvl,tab)
    

    element_type_str = analysis_lvl[:-1].lower() 
    element_title= f"**{element_type_str}:** {main_element}"

    selected_elements,element_column=fetch_selected_elements(analysis_lvl,tab)
    display_element_info(data=data,
                         element_title=element_title,
                         analysis_lvl=analysis_lvl,
                         selected_element=main_element,
                         element_column=element_column)

        
        
    

def right_section(data:pd.DataFrame,
                  global_data:pd.DataFrame,
                  tab:str,
                  **kwargs):
    
    analysis_lvl                     = fetch_analysis_lvl(tab)
    branch                           = fetch_branch(tab)
    period_start,period_end          = load_dates(tab)
    main_element                     = fetch_main_element(analysis_lvl,tab)
    selected_elements,element_column = fetch_selected_elements(analysis_lvl,tab)
    include_outliers                 = fetch_include_outliers(tab)

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
                    main_element=main_element,
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
                       branch_storage=kwargs["branch_storage"],
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
                     
def load_dates(tab:str)->tuple[datetime.date,datetime.date]:
    today = datetime.date.today() 
    start_date,end_date = fetch_dates(tab)

    if start_date is None:
        if today.day < 15:
            if today.month == 1:
                period_start =  datetime.date(today.year, 12 , 15) 
            else:
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
                if data.empty:
                    print('Dataset vacío')
                top_product,top_category = calculate_top_product_and_category(data=data,
                                                                            period_start=period_start,
                                                                            period_end=period_end)
                frequent_branch = calculate_frequent_branch(data=data,
                                                            top_product=top_product)
                
                product_list = list( data["product_id"].unique() )
                category_list = list( data["category"].unique() )
                branch_list = list( data["branch"].unique() )


                # Sucursal en donde se vende más seguido el producto más vendido
                
                option_list    = {"branches"  : branch_list,
                                  "categories": category_list,
                                  "products"  : product_list}
        
                default_values = {"branch"  : frequent_branch,
                                  "category": top_category,
                                  "product" : top_product}

                

            left_section(data=data,
                         option_lists=option_list,
                         default_values=default_values,
                         tab='ventas')
                                                                                                                                                            
        
        with right:
            right_section(data=data,
                          global_data=global_data,
                          tab='ventas')

        

# ===========================================================
#                       ANÁLISIS INVENTARIO
# ===========================================================


    with stock:

        left, right = st.columns([1.2, 3])

        with left:
            option_list    = {"branches"  : branch_list,
                            "categories": category_list,
                            "products"  : product_list}
            
            default_values = {"branch"  : frequent_branch,
                            "category": top_category,
                            "product" : top_product}

            left_section(data=data,
                            option_lists=option_list,
                            default_values=default_values,
                            tab='inventario')
                
            inv_period_start,inv_period_end = load_dates(tab='inventario')
            inv_analysis_lvl = fetch_analysis_lvl(tab='inventario')
            inv_selected_elements,inv_element_column = fetch_selected_elements(inv_analysis_lvl,tab='inventario')
        
            with st.spinner("Cargando datos de inventario..."):
                inv_data_dict = load_inventory_data(inv_period_start,inv_period_end,element_column=inv_element_column,elements_selected=inv_selected_elements)

            inventory = inv_data_dict["inventory"]
            branch_storage = inv_data_dict["branch_storage"]
            
            

            if data.empty:
                    print('Dataset vacío')
                        
            
        with right:
            right_section(data=inventory,
                        branch_storage = branch_storage,
                        global_data=global_data,
                        tab='inventario')
        


if __name__ == "__main__":
    main()