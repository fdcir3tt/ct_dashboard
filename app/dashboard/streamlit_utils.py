import datetime 
import streamlit as st

def pick_date(label: str, 
              default: datetime.datetime = None, 
              key: str = "selected_date")->datetime.date:
    """
    Renderiza un selector de fecha en Streamlit con estado persistente.

    Inicializa la clave en `st.session_state` con el valor por defecto
    si aún no existe.

    Parameters
    ----------
    label : str
        Texto descriptivo que se muestra sobre el selector de fecha.
    default : datetime.datetime, optional
        Valor inicial del selector si la clave no existe en session_state.
        Por defecto None.
    key : str, optional
        Clave de identificación en `st.session_state`. Por defecto
        `'selected_date'`.

    Returns
    -------
    datetime.date
        Fecha seleccionada por el usuario.
    """
    if key not in st.session_state:
        st.session_state[key] = default
    
    return st.date_input(label, key=key)


def pick_elements(label: str,
                  options:list,
                  default: list[str]= None, 
                  key: str = "selected_elements")->list[str]:
    """
    Renderiza un selector múltiple en Streamlit con estado persistente.

    Inicializa la clave en `st.session_state` con el valor por defecto
    si aún no existe. Limita la selección a un máximo de 4 elementos.

    Parameters
    ----------
    label : str
        Texto descriptivo que se muestra sobre el selector.
    options : list
        Lista de opciones disponibles para seleccionar.
    default : list of str, optional
        Valores seleccionados por defecto si la clave no existe en
        session_state. Por defecto None.
    key : str, optional
        Clave de identificación en `st.session_state`. Por defecto
        `'selected_elements'`.

    Returns
    -------
    list of str
        Lista de elementos seleccionados por el usuario (máximo 4).
    """
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
    """
    Renderiza un selector de opción única (radio) en Streamlit con
    estado persistente.

    Inicializa la clave en `st.session_state` con el valor por defecto
    si aún no existe.

    Parameters
    ----------
    label : str
        Texto descriptivo que se muestra sobre el selector.
    options : list
        Lista de opciones disponibles.
    default : str, optional
        Valor seleccionado por defecto si la clave no existe en
        session_state. Por defecto None.
    key : str, optional
        Clave de identificación en `st.session_state`. Por defecto
        `'selected_element'`.

    Returns
    -------
    str
        Opción seleccionada por el usuario.
    """
    if key not in st.session_state:
        st.session_state[key] = default
    
    return st.radio(label=label,
                    options= options,
                    key=key)

def pick_branch(label:str,
                options:list,
                default:str,
                index:int,
                key:str='selected branch')->str:
    """
    Renderiza un selector desplegable de sucursal en Streamlit con
    estado persistente.

    Inicializa la clave en `st.session_state` con el valor por defecto
    si aún no existe.

    Parameters
    ----------
    label : str
        Texto descriptivo que se muestra sobre el selector.
    options : list
        Lista de sucursales disponibles.
    default : str
        Valor seleccionado por defecto si la clave no existe en
        session_state.
    index : int
        Índice de la opción seleccionada por defecto en `options`.
        Actualmente no utilizado internamente por `st.selectbox` en
        esta implementación.
    key : str, optional
        Clave de identificación en `st.session_state`. Por defecto
        `'selected branch'`.

    Returns
    -------
    str
        Nombre de la sucursal seleccionada por el usuario.
    """
    if key not in st.session_state:
        st.session_state[key] = default

    return st.selectbox(label=label, 
                              options=options,
                              key=key)

def load_css(file_name):
    """
    Carga e inyecta un archivo CSS personalizado en la aplicación Streamlit.

    Lee el archivo indicado y lo inserta como bloque `<style>` en el HTML
    de la página usando `st.markdown` con `unsafe_allow_html=True`.

    Parameters
    ----------
    file_name : str
        Ruta al archivo `.css` que se desea cargar.

    Returns
    -------
    None
    """
    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

def fetch_main_element(analysis_lvl:str,tab:str)->str:
    """
    Recupera el elemento principal de análisis desde `st.session_state`.

    Construye la clave de session_state a partir del nivel de análisis
    y la pestaña activa.

    Parameters
    ----------
    analysis_lvl : str
        Nivel de análisis activo, e.g. `'Productos'` o `'Categorías'`.
        Se convierte a singular en minúsculas para formar la clave.
    tab : str
        Nombre de la pestaña activa del dashboard, usado como sufijo
        en la clave de session_state.

    Returns
    -------
    str
        Identificador del elemento principal seleccionado, e.g. un
        `product_id` o nombre de categoría.
    """
    element_type_str = analysis_lvl[:-1].lower() 
    key_str = f'{element_type_str} de análisis {tab}'
    main_element = st.session_state.get(key=key_str)
    return main_element
    
def fetch_analysis_lvl(tab:str)->str:
    """
    Recupera el nivel de análisis activo desde `st.session_state`.

    Parameters
    ----------
    tab : str
        Nombre de la pestaña activa del dashboard, usado como sufijo
        en la clave de session_state.

    Returns
    -------
    str
        Nivel de análisis seleccionado, e.g. `'Productos'` o `'Categorías'`.
    """
    key_str = f'Nivel de análisis {tab} seleccionado'
    analysis_lvl = st.session_state.get(key=key_str)
    return analysis_lvl
   
def fetch_selected_elements(analysis_lvl:str,tab:str)->tuple[list[str],str]:
    """
    Recupera los elementos seleccionados y la columna clasificadora
    correspondiente desde `st.session_state`.

    Determina la clave de session_state según el nivel de análisis,
    aplicando la concordancia de género gramatical correcta en español
    (`'Seleccionadas'` para categorías, `'Seleccionados'` para productos).

    Parameters
    ----------
    analysis_lvl : str
        Nivel de análisis activo. Valores válidos: `'Productos'`,
        `'Categorías'`.
    tab : str
        Nombre de la pestaña activa del dashboard, usado como sufijo
        en la clave de session_state.

    Returns
    -------
    selected_elements : list of str
        Lista de elementos seleccionados por el usuario.
    element_column : str
        Nombre de la columna clasificadora correspondiente al nivel de
        análisis: `'product_id'` para `'Productos'` o `'category'`
        para `'Categorías'`.
    """
    element_column={"Productos" :"product_id","Categorías":"category"}[analysis_lvl]
    if analysis_lvl=="Categorías":
        key_str = f"Sucursal {analysis_lvl} Seleccionadas {tab}"
    else:
        key_str = f"Sucursal {analysis_lvl} Seleccionados {tab}"
    selected_elements = st.session_state.get(key=key_str)

    return selected_elements,element_column

def fetch_dates(tab:str)->tuple[datetime.date,datetime.date]:
    """
    Recupera las fechas de inicio y fin del período de análisis
    desde `st.session_state`.

    Parameters
    ----------
    tab : str
        Nombre de la pestaña activa del dashboard, usado como sufijo
        en las claves de session_state `'Sucursal Inicio {tab}'` y
        `'Sucursal Fin {tab}'`.

    Returns
    -------
    start_date : datetime.date
        Fecha de inicio del período de análisis.
    end_date : datetime.date
        Fecha de fin del período de análisis.
    """
    start_date = st.session_state.get(f"Sucursal Inicio {tab}")
    end_date = st.session_state.get(f"Sucursal Fin {tab}")


    return start_date,end_date

def fetch_branch(tab:str)->str:
    """
    Recupera la sucursal seleccionada desde `st.session_state`.

    Parameters
    ----------
    tab : str
        Nombre de la pestaña activa del dashboard, usado como sufijo
        en la clave de session_state `'Sucursal seleccionada {tab}'`.

    Returns
    -------
    str
        Nombre de la sucursal seleccionada por el usuario.
    """
    key_str =f'Sucursal seleccionada {tab}'
    branch = st.session_state.get(key=key_str)
    return branch

def fetch_include_outliers(tab:str)->bool:
    """
    Recupera y convierte la preferencia de inclusión de valores atípicos
    desde `st.session_state`.

    Lee el valor almacenado bajo la clave `'Incluir {tab} anómalas'` y
    lo convierte de string (`'Sí'` / otro valor) a booleano.

    Parameters
    ----------
    tab : str
        Nombre de la pestaña activa del dashboard, usado como sufijo
        en la clave de session_state.

    Returns
    -------
    bool
        True si el usuario seleccionó incluir valores atípicos (`'Sí'`),
        False en cualquier otro caso.
    """
    key_str=f'Incluir {tab} anómalas'
    outliers = st.session_state.get(key=key_str)
    if outliers=='Sí':
        include_outliers = True
    else:
        include_outliers = False
    
    return include_outliers 