import pandas as pd
import datetime
import streamlit as st

from matplotlib.figure import Figure
from dashboard.utils import growth_rate,top_n
from dashboard.graphs import period_sales,period_inventory,sales_hist,render_sales_heat_map,prepare_sales_heatmap_data,GraphFilters,GraphFilterConfig,abc_bar_chart

def sales_plots(data:pd.DataFrame,
                    selected_elements:list,
                    element_column:str,
                    branch:str,
                    include_outliers :bool,
                    period_start,period_end)->tuple[Figure,Figure]:

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
    col1, col2 = st.columns(2)
    with col1:
        st.pyplot(branch_period_sales_fig)
    with col2:
        st.pyplot(global_period_sales_fig)



def inventory_plots(inventory:pd.DataFrame,
                        branch_storage:dict,
                        selected_elements:list,
                        element_column:str,
                        branch:str,
                        period_start,
                        period_end)->tuple[Figure,Figure]:   
                 
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
    return branch_period_inventory_fig,global_period_inventory_fig

 
def kpi_calculator(data:pd.DataFrame,
                    selected_element:str,
                    element_column:str,
                    period_start,
                    include_outliers:bool|None,
                    tab:str,
                    branch:str=None)->dict[str,float]|None:
    
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
    
    if tab=='ventas':
        current_sales,current_cost,current_profit = sales_kpis(data=filtered_current)
        prev_sales,prev_cost,prev_profit = sales_kpis(data=filtered_prev)
            
        sales_rate = growth_rate(current_sales, prev_sales)
        profit_rate = growth_rate(current_profit, prev_profit)
        cost_rate = growth_rate(current_cost, prev_cost)

        

        return {"sales_rate":sales_rate ,"profit_rate":profit_rate,"cost_rate":cost_rate,"current_sales":current_sales,"current_profit":current_profit,"current_cost":current_cost}
    if tab=='inventario':
        current_stock,current_supplied= inventory_kpis(data=filtered_current)
        prev_stock,prev_supplied = inventory_kpis(data=filtered_prev)
            
        stock_rate = growth_rate(current_stock, prev_stock)
        supply_rate = growth_rate(current_supplied, prev_supplied)
            

        
        return {"stock_rate":stock_rate,"supply_rate":supply_rate,"current_stock":current_stock,"current_supplied":current_supplied}     

def kpi_display(rates_dict:dict[str,float]|None,tab:str,title:str)->None:
    if rates_dict is None:
         return None
    if tab=="ventas":
        sales_rate = rates_dict["sales_rate"]
        profit_rate = rates_dict["profit_rate"]
        cost_rate = rates_dict["cost_rate"]

        current_sales =rates_dict["current_sales"]
        current_profit =rates_dict["current_profit"]
        current_cost =rates_dict["current_cost"]

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
                            unsafe_allow_html=True) 
              
    if tab=="inventario":
        stock_rate = rates_dict["stock_rate"]
        supply_rate = rates_dict["supply_rate"]
        
        current_stock = rates_dict["current_stock"]
        current_supplied = rates_dict["current_supplied"]

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
                

def display_element_info(data:pd.DataFrame,
                 element_title:str,
                 analysis_lvl:str,
                 selected_element:str,
                 element_column:str)->None:
    def get_element_info(element_data:pd.DataFrame,element_column:str)->dict[str,str|float]:
        top_clients = list ( top_n(element_data,element_column,type="cliente")["clientId"] )
        clients_str=''
        for client in top_clients:
            clients_str+=client+','
        clients_str = clients_str[:-1]

        element_info = {
            "cost_per_unit" : round(element_data["cost"].max(),2),
            "price_range":( round(element_data["price"].min(),2) , round( element_data["price"].max(),2) ),
            "category":element_data["category"].iloc[0],
            "clients_str":clients_str }
        return element_info
        
    is_element = data[element_column]== selected_element
    filtered = data[is_element]
    if filtered.empty:
        st.warning("No hay datos para el elemento seleccionado en este periodo.")
        st.stop()

    element_info = get_element_info(filtered,element_column)
    category = element_info["category"]
    cost_per_unit = element_info["cost_per_unit"]
    price_range = element_info["price_range"]
    clients_str = element_info["clients_str"]

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
                            str(selected_element),
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

def histogram_plots(data:pd.DataFrame,
                        element_column:str,
                        main_element:str,
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
            print(type(branch_histogram))
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
                    merged = prepare_sales_heatmap_data(
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
                merged = prepare_sales_heatmap_data(
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