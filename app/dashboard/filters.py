from datetime import date
from dashboard.streamlit_utils import pick_branch,pick_elements,pick_main_element,pick_date

def include_outliers_filter(tab:str)->bool|None:
    if tab=='ventas':
            outliers= pick_main_element(label='Análisis con ventas anomalas incluídas',
                                            options= ['Sí','No'],
                                            default='Sí',
                                            key=f'Incluir {tab} anómalas')
            if outliers=='Sí':
                include_outliers = True
            else: 
                include_outliers = False
    else:
        include_outliers = None 
    return include_outliers

def analysis_lvl_filter(tab:str)->str:
    analysis_lvl = pick_main_element(label='Nivel de análisis',
                                             options=["Productos","Categorías"],
                                             default='Productos',
                                             key=f'Nivel de análisis {tab} seleccionado')
    return analysis_lvl

                
def branch_filter(branch_list:list[str],branch_index:int,tab:str)->str:             
    branch = pick_branch(label='Sucursal',
                             options=branch_list,
                             index=branch_index,
                             key=f'Sucursal seleccionada {tab}')
    return branch


        
def products_filter(product_list:list[str],top_product:str,analysis_lvl:str,tab:str)->list[str]:
        if analysis_lvl=="Productos":
                products = pick_elements(label="Producto(s)",
                                         options=product_list,
                                         default=[top_product],
                                         key=f"Sucursal Productos Seleccionados {tab}")
        if analysis_lvl=="Categorías":
                products = []
        return products    
                
       
def categories_filter(category_list:list[str],top_category:str,analysis_lvl:str,tab:str)->list[str]:
        if analysis_lvl=="Productos":
                categories = []
            
        if analysis_lvl=="Categorías":
                
                categories = pick_elements(label="Categoría(s)",
                                           options=category_list,
                                           default=[top_category],
                                           key=f"Sucursal Categorías Seleccionadas {tab}")
        return categories

def main_element_filter(analysis_lvl:str,element_list:list[str],top_element:str,tab:str)->tuple[str,str]:
    element_type_str = analysis_lvl[:-1].lower() 
    label = f'{element_type_str.title()} de análisis'
    key_str = f'{element_type_str} de análisis {tab}'
    
    main_element = pick_main_element(label=label,
                                        options= element_list,
                                        key=key_str,
                                        default=top_element)
    element_title= f"**{element_type_str}:** {main_element}"
    return main_element,element_title

def period_filter(start_date:date,end_date:date,tab:str)->tuple[date,date]:
        period_start = pick_date(label='Inicio',
                                 default=start_date,
                                 key=f'Sucursal Inicio {tab}')
        period_end = pick_date(label='Fin',
                               default=end_date,
                               key=f'Sucursal Fin {tab}')   
        return period_start,period_end