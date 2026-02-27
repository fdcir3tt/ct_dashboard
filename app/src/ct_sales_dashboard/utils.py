import streamlit as st
import yaml
import streamlit_authenticator as stauth
import streamlit.components.v1 as components
from yaml.loader import SafeLoader
from functools import wraps

def clear_cookies():
    cookie_name = "cookie_name"
    components.html(f"""
    <script>
    document.cookie = "{cookie_name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
    window.location.reload();
    </script>
    """)

def load_css(file_name):

    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def load_authenticator():
    with open("auth.yml") as file:
        config = yaml.load(file, Loader=SafeLoader)

    authenticator = stauth.Authenticate(
        credentials=config["credentials"],
        cookie_name=config["cookie"]["name"],
        cookie_key=config["cookie"]["key"],
        cookie_expiry_days=config["cookie"]["expiry_days"],
    )
    return authenticator

def protect_page(func):
    """
    Decorador para proteger págonas de la aplicación de Streamlit.
    Muestra página de inicio, define st.session_state, agrega botón de logout 
    """
    authenticator = load_authenticator()

    @wraps(func)
    def wrapper(*args, **kwargs):

        authentication_status = st.session_state.get("authentication_status")
        

        if authentication_status:
            # Mostrar botón de cerrar sesión
            col1, col2 = st.columns([9, 1])
            with col2:
                
                if st.button("Cerrar sesión"):
                    # Solo si ya esta ingresado
                    authenticator.logout("Logout",location= "unrendered")

                    # Reiniciar sesión
                    st.session_state.clear()
                    st.switch_page('app.py')

            return func(*args, **kwargs)  

        elif authentication_status == False:
            st.error("Credenciales incorrectas")
            st.stop()
        elif authentication_status == None:
            st.warning("Por favor ingrese sus credenciales correctamente")
            st.stop()

    return wrapper