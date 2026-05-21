import datetime 
import streamlit as st

def pick_date(label: str, 
              default: datetime.datetime = None, 
              key: str = "selected_date")->datetime.date:
    
    if key not in st.session_state:
        st.session_state[key] = default
    
    return st.date_input(label, key=key)


def pick_elements(label: str,
                  options:list,
                  default: list[str]= None, 
                  key: str = "selected_elements")->list[str]:
    
    if key not in st.session_state:
        st.session_state[key] = default

    return st.multiselect(label, 
                          options ,
                          max_selections= 4 ,
                          key=key)
    

def pick_main_element(label: str,
                      options:list,
                      default: str= None, 
                      key: str = "selected_element")->str:
    
    if key not in st.session_state:
        st.session_state[key] = default
    
    return st.radio(label=label,
                    options= options,
                    key=key)

def pick_branch(label:str,
                options:list,
                index:int,
                key:str='selected branch')->str:
    
    if key not in st.session_state:
        st.session_state[key] = index

    return st.selectbox(label=label, 
                              options=options,
                              key=key)

def load_css(file_name):

    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

def fetch_main_element(analysis_lvl:str,tab:str)->str:
    element_type_str = analysis_lvl[:-1].lower() 
    key_str = f'{element_type_str} de análisis {tab}'
    main_element = st.session_state.get(key=key_str)
    return main_element
    
def fetch_analysis_lvl(tab:str)->str:
    key_str = f'Nivel de análisis {tab} seleccionado'
    analysis_lvl = st.session_state.get(key=key_str)
    return analysis_lvl
   
def fetch_selected_elements(analysis_lvl:str,tab:str)->tuple[list[str],str]:
    element_column={"Productos" :"product_id","Categorías":"category"}[analysis_lvl]
       
    key_str = f"Sucursal {analysis_lvl} Seleccionados {tab}"
    selected_elements = st.session_state.get(key=key_str)

    return selected_elements,element_column

def fetch_dates(tab:str)->tuple[datetime.date,datetime.date]:
    
    start_date = st.session_state.get(f"Sucursal Inicio {tab}")
    end_date = st.session_state.get(f"Sucursal Fin {tab}")


    return start_date,end_date

def fetch_branch(tab:str)->str:
    key_str =f'Sucursal seleccionada {tab}'
    branch = st.session_state.get(key=key_str)
    return branch

def fetch_include_outliers(tab:str)->bool:
    key_str=f'Incluir {tab} anómalas'
    outliers = st.session_state.get(key=key_str)
    if outliers=='Sí':
        include_outliers = True
    else:
        include_outliers = False
    
    return include_outliers 