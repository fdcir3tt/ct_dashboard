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