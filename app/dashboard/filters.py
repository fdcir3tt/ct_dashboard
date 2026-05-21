from datetime import date
from dashboard.streamlit_utils import pick_branch,pick_elements,pick_main_element,pick_date

def include_outliers_filter(tab:str)->str|None:
    """
    Determina si se deben incluir ventas anómalas en el análisis.

    Cuando la pestaña seleccionada es ``'ventas'``, se muestra un selector
    para decidir si las ventas anómalas deben incluirse en el análisis.
    Para cualquier otro valor de ``tab``, la función retorna ``None``.

    Parameters
    ----------
    tab : str
        Nombre de la pestaña o contexto de análisis.

    Returns
    -------
    bool or None
        - ``True`` si se incluyen las ventas anómalas.
        - ``False`` si no se incluyen.
        - ``None`` si el análisis no corresponde a la pestaña ``'ventas'``.

    Notes
    -----
    La selección se realiza mediante el componente ``pick_main_element``.

    Examples
    --------
    >>> include_outliers_filter("ventas")
    True

    >>> include_outliers_filter("inventario")
    None
    """
    if tab=='ventas':
        outliers= pick_main_element(label='Análisis con ventas anomalas incluídas',
                                            options= ['Sí','No'],
                                            default='Sí',
                                            key=f'Incluir {tab} anómalas')
    if tab=='inventario':
        outliers=None
            
    return outliers

def analysis_lvl_filter(tab:str)->str:
    """
    Obtiene el nivel de análisis seleccionado por el usuario.

    Muestra un selector para definir si el análisis se realizará
    a nivel de productos o categorías.

    Parameters
    ----------
    tab : str
        Nombre de la pestaña o contexto utilizado para generar
        la clave única del componente.

    Returns
    -------
    str
        Nivel de análisis seleccionado. Puede ser:

        - ``"Productos"``
        - ``"Categorías"``

    Notes
    -----
    La selección se realiza mediante el componente ``pick_main_element``.

    Examples
    --------
    >>> analysis_lvl_filter("ventas")
    'Productos'
    """
    analysis_lvl = pick_main_element(label='Nivel de análisis',
                                             options=["Productos","Categorías"],
                                             default='Productos',
                                             key=f'Nivel de análisis {tab} seleccionado')
    return analysis_lvl

                
def branch_filter(branch_list:list[str],branch_index:int,tab:str)->str:
    """
    Obtiene la sucursal seleccionada por el usuario.

    Muestra un selector para elegir una sucursal dentro de la lista
    proporcionada.

    Parameters
    ----------
    branch_list : list of str
        Lista de sucursales disponibles para selección.
    branch_index : int
        Índice de la sucursal seleccionada por defecto.
    tab : str
        Nombre de la pestaña o contexto utilizado para generar
        la clave única del componente.

    Returns
    -------
    str
        Nombre de la sucursal seleccionada.

    Notes
    -----
    La selección se realiza mediante el componente ``pick_branch``.

    Examples
    --------
    >>> branch_filter(["Centro", "Norte"], 0, "ventas")
    'CD. OBREGON, SON.'
    """             
    branch = pick_branch(label='Sucursal',
                             options=branch_list,
                             index=branch_index,
                             key=f'Sucursal seleccionada {tab}')
    return branch


        
def products_filter(product_list:list[str],top_product:str,analysis_lvl:str,tab:str)->list[str]:
    """
    Obtiene los productos seleccionados para el análisis.

    Si el nivel de análisis es ``"Productos"``, se muestra un selector
    múltiple de productos. En caso contrario, retorna una lista vacía.

    Parameters
    ----------
    product_list : list of str
        Lista de productos disponibles.
    top_product : str
        Producto seleccionado por defecto.
    analysis_lvl : str
        Nivel de análisis seleccionado. Puede ser ``"Productos"``
        o ``"Categorías"``.
    tab : str
        Nombre de la pestaña o contexto utilizado para generar
        la clave única del componente.

    Returns
    -------
    list of str
        Lista de productos seleccionados. Si el nivel de análisis es
        ``"Categorías"``, retorna una lista vacía.

    Notes
    -----
    La selección se realiza mediante el componente ``pick_elements``.

    Examples
    --------
    >>> products_filter(["A", "B"], "A", "Productos", "ventas")
    ['A']
    """
    if analysis_lvl=="Productos":
            products = pick_elements(label="Producto(s)",
                                         options=product_list,
                                         default=[top_product],
                                         key=f"Sucursal Productos Seleccionados {tab}")
    if analysis_lvl=="Categorías":
                products = []
    return products    
                
       
def categories_filter(category_list:list[str],top_category:str,analysis_lvl:str,tab:str)->list[str]:
    """
    Obtiene las categorías seleccionadas para el análisis.

    Si el nivel de análisis es ``"Categorías"``, se muestra un selector
    múltiple de categorías. En caso contrario, retorna una lista vacía.

    Parameters
    ----------
    category_list : list of str
        Lista de categorías disponibles.
    top_category : str
        Categoría seleccionada por defecto.
    analysis_lvl : str
        Nivel de análisis seleccionado. Puede ser ``"Productos"``
        o ``"Categorías"``.
    tab : str
        Nombre de la pestaña o contexto utilizado para generar
        la clave única del componente.

    Returns
    -------
    list of str
        Lista de categorías seleccionadas. Si el nivel de análisis es
        ``"Productos"``, retorna una lista vacía.

    Notes
    -----
    La selección se realiza mediante el componente ``pick_elements``.

    Examples
    --------
    >>> categories_filter(["Bebidas", "Snacks"], "Bebidas", "Categorías", "ventas")
    ['Bebidas']
    """
    if analysis_lvl=="Productos":
        categories = []
            
    if analysis_lvl=="Categorías":
                
        categories = pick_elements(label="Categoría(s)",
                                           options=category_list,
                                           default=[top_category],
                                           key=f"Sucursal Categorías Seleccionadas {tab}")
    return categories

def main_element_filter(analysis_lvl:str,element_list:list[str],default_element:str,tab:str)->str:
    """
    Obtiene el elemento principal seleccionado para el análisis.

    Genera dinámicamente un selector dependiendo del nivel de análisis
    y construye un título descriptivo asociado al elemento elegido.

    Parameters
    ----------
    analysis_lvl : str
        Nivel de análisis seleccionado, por ejemplo ``"Productos"``
        o ``"Categorías"``.
    element_list : list of str
        Lista de elementos disponibles para selección.
    top_element : str
        Elemento seleccionado por defecto.
    tab : str
        Nombre de la pestaña o contexto utilizado para generar
        la clave única del componente.

    Returns
    -------
    tuple of str
        Tupla con:

        - ``main_element`` : elemento seleccionado.
        - ``element_title`` : texto descriptivo formateado para mostrar.

    Notes
    -----
    La selección se realiza mediante el componente ``pick_main_element``.

    Examples
    --------
    >>> main_element_filter(
    ...     "Productos",
    ...     ["ACC2", "XRX"],
    ...     "ACC2",
    ...     "ventas"
    ... )
    ('ACC2', '**producto:** ACC2')
    """
    element_type_str = analysis_lvl[:-1].lower() 
    label = f'{element_type_str.title()} de análisis'
    key_str = f'{element_type_str} de análisis {tab}'
    
    main_element = pick_main_element(label=label,
                                        options= element_list,
                                        key=key_str,
                                        default=default_element)
    element_title= f"**{element_type_str}:** {main_element}"
    return main_element

def period_filter(start_date:date,end_date:date,tab:str)->tuple[date,date]:
    """
    Obtiene el periodo de fechas seleccionado para el análisis.

    Muestra dos selectores de fecha para definir el inicio y fin
    del periodo de análisis.

    Parameters
    ----------
    start_date : date
        Fecha inicial por defecto.
    end_date : date
        Fecha final por defecto.
    tab : str
        Nombre de la pestaña o contexto utilizado para generar
        las claves únicas de los componentes.

    Returns
    -------
    tuple of date
        Tupla con:

        - ``period_start`` : fecha inicial seleccionada.
        - ``period_end`` : fecha final seleccionada.

    Notes
    -----
    La selección se realiza mediante el componente ``pick_date``.

    Examples
    --------
    >>> period_filter(date(2024, 1, 1), date(2024, 12, 31), "ventas")
    (date(2024, 1, 1), date(2024, 12, 31))
    """
    period_start = pick_date(label='Inicio',
                                 default=start_date,
                                 key=f'Sucursal Inicio {tab}')
    period_end = pick_date(label='Fin',
                               default=end_date,
                               key=f'Sucursal Fin {tab}')   
    return period_start,period_end