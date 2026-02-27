import streamlit as st
from ct_sales_dashboard.utils import load_authenticator,load_css,clear_cookies



st.set_page_config(
    page_title="CT Dashboard Login",
    layout="wide",  
    initial_sidebar_state="collapsed" 
)

load_css("assets/styles.css")

authenticator = load_authenticator()


col1, col2 = st.columns([1, 10])
with col1:
    st.image("assets/logo.png", width=50)

with col2:
    st.markdown("### Dashboard CT International")
           
        
# ===========================================================
#                       LOGIN
# ===========================================================

#if st.button("Reset"):
#    st.session_state.clear()  
#    clear_cookies()

authenticator.login(location='main', fields={"Login": "Inicio",
                                             "Username": "Usuario",
                                             "Password":"Contraseña"})
authentication_status = st.session_state.get("authentication_status")


if authentication_status:
    st.switch_page("pages/dashboard.py")
elif authentication_status is False:
    st.error("Usuario/contraseña incorrecta")
else:
    st.warning("Por favor ingrese sus credenciales")