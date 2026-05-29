import pandas as pd
import geopandas as gpd
import numpy as np
import folium
import warnings
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.patches as mpatches
import matplotlib as mpl
import io
import base64

from datetime import date
from dataclasses import dataclass
from dashboard.utils import month_dict,Date
from streamlit_folium import st_folium
from matplotlib.ticker import MaxNLocator
from matplotlib.figure import Figure

warnings.filterwarnings('ignore')

@dataclass
class GraphFilterConfig:
    """
    Configuración de filtros para las gráficas del dashboard.

    Parameters
    ----------
    start_date : date
        Fecha de inicio del período de análisis.
    end_date : date
        Fecha de fin del período de análisis.
    element_column : str, optional
        Nombre de la columna clasificadora de elementos, e.g. `'product_id'`
        o `'category'`. Por defecto None.
    selected_elements : list, optional
        Lista de valores a incluir en el filtro de `element_column`.
        Por defecto None.
    branch : str, optional
        Nombre de la sucursal a filtrar. Si es None, no se aplica filtro
        por sucursal. Por defecto None.
    include_outliers : bool, optional
        Si es False, excluye registros donde `is_outlier` sea True.
        Si es None, no se aplica filtro de outliers. Por defecto None.
    val : bool, optional
        Indica si la función que usa esta configuración está en modo de
        pruebas unitarias, retornando datos adicionales. Por defecto False.

    Attributes
    ----------
    start_date : date
    end_date : date
    element_column : str or None
    selected_elements : list or None
    branch : str or None
    include_outliers : bool or None
    val : bool
    """
    start_date: date
    end_date: date
    element_column: str | None = None
    selected_elements: list | None = None
    branch: str | None = None
    include_outliers: bool | None= None
    val: bool = False

class GraphFilters:
    """
    Aplica filtros estandarizados a DataFrames para las visualizaciones
    del dashboard.

    Encapsula la lógica de filtrado por fecha, elemento, sucursal y
    outliers, así como la generación de figuras vacías cuando no hay
    datos disponibles tras el filtrado.

    Parameters
    ----------
    config : GraphFilterConfig
        Objeto de configuración con todos los parámetros de filtrado.

    Attributes
    ----------
    cfg : GraphFilterConfig
        Configuración de filtros activa para esta instancia.

    Methods
    -------
    apply(data)
        Aplica los filtros configurados a un DataFrame.
    empty_plot(df)
        Genera una figura vacía con mensaje de aviso.

    Examples
    --------
    >>> config = GraphFilterConfig(
    ...     start_date=date(2024, 1, 1),
    ...     end_date=date(2024, 1, 31),
    ...     element_column='product_id',
    ...     selected_elements=['P001', 'P002'],
    ...     include_outliers=False
    ... )
    >>> filters = GraphFilters(config=config)
    >>> df_filtered = filters.apply(data)
    """
    def __init__(self, config: GraphFilterConfig):
        self.cfg = config

    def apply(self, data: pd.DataFrame):
        """
        Aplica los filtros configurados a un DataFrame de datos.

        Parameters
        ----------
        data : pd.DataFrame
            DataFrame con columnas `date`, `is_outlier`, `branch`, y la columna
            de elemento definida en `cfg.element_column`.

        Returns
        -------
        pd.DataFrame
            Subconjunto del DataFrame original con los filtros aplicados.
        """
        mask = (
            (data['date'] >= self.cfg.start_date) &
            (data['date'] <= self.cfg.end_date) 
        )
        if self.cfg.element_column :
            mask &= data[self.cfg.element_column].isin(self.cfg.selected_elements)

        if self.cfg.include_outliers is False:
            mask &= data["is_outlier"] == False

        df = data[mask]

        if self.cfg.branch:
            df = df[df["branch"] == self.cfg.branch]

        return df

    def empty_plot(self, df):
        """
        Genera una figura vacía con mensaje de aviso cuando no hay datos disponibles.

        Parameters
        ----------
        df : pd.DataFrame
            DataFrame vacío que se retorna junto con la figura cuando `cfg.val` es True.

        Returns
        -------
        matplotlib.figure.Figure
            Figura con mensaje "No hay datos disponibles" si `cfg.val` es False.
        tuple[matplotlib.figure.Figure, pd.DataFrame]
            Tupla de figura y DataFrame vacío si `cfg.val` es True.
        """
        if df.empty:
            fig, ax = plt.subplots(figsize=(8, 4))
            ax.text(0.5, 0.5, "No hay datos disponibles",
                    ha="center", va="center", fontsize=14)
            ax.axis("off")

            return (fig, df) if self.cfg.val else fig

def load_mexico_shp():
    """
    Carga y prepara el shapefile de estados de México para uso en mapas de calor.

    Lee el archivo `gadm41_MEX_1.shp`, simplifica las geometrías para reducir
    el tamaño de renderizado y normaliza los nombres de estado a mayúsculas.

    Returns
    -------
    geopandas.GeoDataFrame
        GeoDataFrame con columnas de geometría simplificada y `state` en mayúsculas.
    """
    mexico = gpd.read_file("data/raw/gadm41_MEX_shp/gadm41_MEX_1.shp")
    mexico["geometry"] = mexico["geometry"].simplify(
        tolerance=0.01, preserve_topology=True
    )
    mexico["state"] = mexico["NAME_1"].str.upper()
    return mexico


# -----------------------------------------------------------
# GRÄFICAS
# -----------------------------------------------------------

def period_sales(data: pd.DataFrame, selected_elements: list[str] ,element_column:str ,start_date:Date, end_date:Date,include_outliers:bool|None=None,branch:str|None=None,val:bool=False)->Figure|tuple[Figure,pd.DataFrame]:
    """
    Genera una gráfica de curva de ventas con recta de tendencia por período.

    Parameters
    ----------
    data : pd.DataFrame
        Datos de facturas de venta. Debe contener las columnas `date`,
        `quantity`, `branch`, `is_outlier`, y la columna indicada en
        `element_column`.
    selected_elements : list of str
        Lista de identificadores de los elementos a visualizar
        (e.g. IDs de producto o nombres de categoría).
    element_column : str
        Nombre de la columna clasificadora de elementos.
        Use `'product_id'` para productos o `'category'` para categorías.
    start_date : Date
        Fecha de inicio del período de análisis.
    end_date : Date
        Fecha de fin del período de análisis.
    include_outliers : bool, optional
        Si es False, excluye registros marcados como atípicos (`is_outlier == True`).
        Por defecto None (no aplica filtro de outliers).
    branch : str, optional
        Nombre de la sucursal a analizar. Si es None, se realiza análisis global.
    val : bool, optional
        Si es True, retorna también el DataFrame usado para graficar.
        Por defecto False.

    Returns
    -------
    matplotlib.figure.Figure
        Figura con la curva de ventas y recta de tendencia. Se retorna cuando
        `val` es False.
    tuple[matplotlib.figure.Figure, pd.DataFrame]
        Tupla con la figura y el DataFrame graficado. Se retorna cuando
        `val` es True.
    """

    # --- Asegurar que las fechas SON datetime ---
    df = data.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["month"] = df["date"].dt.month
    df["year"] = df["date"].dt.year

    start_date = pd.to_datetime(start_date)
    end_date   = pd.to_datetime(end_date)

    
    filters = GraphFilters(config= GraphFilterConfig(start_date=start_date,
                                                     end_date=end_date,
                                                     element_column=element_column,
                                                     selected_elements=selected_elements,
                                                     branch=branch,
                                                     include_outliers=include_outliers,
                                                     val=val))

    df = filters.apply(df)
    if df.empty:
        return filters.empty_plot(df)
    
    month = month_dict[ df["month"].iloc[0] ]
    year = df["year"].iloc[0]
    
    # Líneas interpoladas
    
    df["sales_day"]   = df.groupby([element_column, "date"])["quantity"].transform("sum")
    
    
        
    fig, ax = plt.subplots(figsize=(12, 6))
    plt.style.use("seaborn-v0_8")
    
    colors = ["#e63947","#39e6c9","#0400ff","#e43d0a"]
    no_data_color = "#ee08db"
    i = 0
    for id in selected_elements:
        is_element = df[element_column]==id
        plot_df = df[is_element]
        if plot_df.empty:
            ax.plot(plot_df["date"], plot_df["sales_day"], label= id+" (no hay datos)",
                marker="o", color=no_data_color)
            continue
        
        
    # === Recta de tendencia === #

    # Convertir fechas a valores numéricos (ordinales)
        plot_df = plot_df[["date","sales_day"]].drop_duplicates()
        plot_df["sales_day"] = plot_df["sales_day"].interpolate(method="linear")
        plot_df = plot_df.sort_values(by="date").reset_index()

        ax.plot(plot_df["date"], plot_df["sales_day"], label= id,
                marker="o", color=colors[i])
        
        x = mdates.date2num(plot_df["date"])
        y = plot_df["sales_day"]

        # Ajuste lineal
        coeffs = np.polyfit(x, y, 1)  # pendiente y ordenada
        trend_fn = np.poly1d(coeffs)

        # Recta suavizada para graficar
        x_smooth = np.linspace(x.min(), x.max(), 200)
        y_smooth = trend_fn(x_smooth)

        # Graficar recta de tendencia
        ax.plot(mdates.num2date(x_smooth), y_smooth,
                color=colors[i], linewidth=2, linestyle="--",
                label="Tendencia")
        i+=1
    if branch:
        title = f"Ventas en {branch} de {month},{year}"
    else:
        title = f"Ventas globales de {month},{year}"
    ax.set_title(title, fontsize=16, fontweight="bold")
    ax.set_xlabel("Fecha")
    ax.set_ylabel("Cantidad")

    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    
    

    # Eje X limpio
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.xticks(rotation=45, ha="right")

    plt.grid(False)
    plt.legend()
    plt.tight_layout()
    
    return (fig, plot_df) if val else fig

def period_inventory(data: pd.DataFrame,branch_storage:dict[str,list[str]], selected_elements: list[str] ,element_column:str ,start_date:Date, end_date:Date,branch:str|None=None,val:bool=False)->Figure|tuple[Figure,pd.DataFrame]:
    """
    Genera una gráfica de curva de existencias (inventario) con recta de tendencia.

    Parameters
    ----------
    data : pd.DataFrame
        Datos de inventario. Debe contener las columnas `date`, `stock`,
        `storage_id`, y la columna indicada en `element_column`.
    branch_storage : dict[str, list[str]] or pd.DataFrame
        Relación entre sucursales y sus almacenes. Puede ser un diccionario
        donde las claves son sucursales y los valores listas de `storage_id`,
        o un DataFrame con columnas `branch` y `storage_id`.
    selected_elements : list of str
        Lista de identificadores de los elementos a visualizar.
    element_column : str
        Nombre de la columna clasificadora de elementos.
        Use `'product_id'` para productos o `'category'` para categorías.
    start_date : Date
        Fecha de inicio del período de análisis.
    end_date : Date
        Fecha de fin del período de análisis.
    branch : str, optional
        Nombre de la sucursal a analizar. Si es None, se realiza análisis global.
    val : bool, optional
        Si es True, retorna también el DataFrame usado para graficar.
        Por defecto False.

    Returns
    -------
    matplotlib.figure.Figure
        Figura con la curva de existencias y recta de tendencia. Se retorna
        cuando `val` es False.
    tuple[matplotlib.figure.Figure, pd.DataFrame]
        Tupla con la figura y el DataFrame graficado. Se retorna cuando
        `val` es True.
    """
    
    # --- Asegurar que las fechas SON datetime ---
    df = data.copy().reset_index(drop=True)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    start_date = pd.to_datetime(start_date)
    end_date   = pd.to_datetime(end_date)

    
    filters = GraphFilters(config= GraphFilterConfig(start_date=start_date,
                                                     end_date=end_date,
                                                     element_column=element_column,
                                                     selected_elements=selected_elements,
                                                     val=val))

    df = filters.apply(df)
    if df.empty:
        return filters.empty_plot(df)
    
    df["month"] = df["date"].dt.month
    df["year"] = df["date"].dt.year
    month = month_dict[ df["month"].iloc[0] ]
    year = df["year"].iloc[0]
    
    if branch:
        if isinstance(branch_storage,dict):
            storages = branch_storage[branch]
        elif isinstance(branch_storage,pd.DataFrame):
            storages = list(branch_storage[branch_storage["branch"]==branch]["storage_id"].unique())
        mask = df['storage_id'].isin(storages)
    else:
        if isinstance(branch_storage,dict):
            storages = []
            for b in branch_storage.values():
                storages+=b

        elif isinstance(branch_storage,pd.DataFrame):
            storages = list(branch_storage["storage_id"].unique())

        mask = df['storage_id'].isin(storages)

    df=df[mask]
    df['total_stock']= df.groupby(['date',element_column])['stock'].transform('sum')
    
    
        
    fig, ax = plt.subplots(figsize=(12, 6))
    plt.style.use("seaborn-v0_8")
    
    colors = ["#e63947","#39e6c9","#0400ff","#e43d0a"]
    no_data_color = "#ee08db"
    i = 0
    for id in selected_elements:
        is_element = df[element_column]==id
        plot_df = df[is_element]
        if plot_df.empty:
            ax.plot(plot_df["date"], plot_df["stock"], label= id+" (no hay datos)",
                marker="o", color=no_data_color)
            continue
        
        
    # === Recta de tendencia === #

    # Convertir fechas a valores numéricos (ordinales)
        plot_df = plot_df[["date","total_stock"]].drop_duplicates()
        plot_df["stock"] = plot_df["total_stock"].interpolate(method="linear")
        plot_df = plot_df.sort_values(by="date").reset_index()

        ax.plot(plot_df["date"], plot_df["total_stock"], label= id,
                marker="o", color=colors[i])
        
        x = mdates.date2num(plot_df["date"])
        y = plot_df["total_stock"]

        # Ajuste lineal
        coeffs = np.polyfit(x, y, 1)  # pendiente y ordenada
        trend_fn = np.poly1d(coeffs)

        # Recta suavizada para graficar
        x_smooth = np.linspace(x.min(), x.max(), 200)
        y_smooth = trend_fn(x_smooth)

        # Graficar recta de tendencia
        ax.plot(mdates.num2date(x_smooth), y_smooth,
                color=colors[i], linewidth=2, linestyle="--",
                label="Tendencia")
        i+=1
    if branch:
        title = f"Existencia en {branch} de {month},{year}"
    else:
        title = f"Existencia global de {month},{year}"
    ax.set_title(title, fontsize=16, fontweight="bold")
    ax.set_xlabel("Fecha")
    ax.set_ylabel("Cantidad")

    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    
    

    # Eje X limpio
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.xticks(rotation=45, ha="right")

    plt.grid(False)
    plt.legend()
    plt.tight_layout()
    
    return (fig, plot_df) if val else fig


def sales_hist(data: pd.DataFrame,main_element: str,
               element_column: str,
               start_date,end_date,
               include_outliers:bool,
               branch: str = None,
               val: bool = False,)->Figure|tuple[Figure,pd.DataFrame]:
    """
    Genera un histograma de frecuencias de ventas diarias para un elemento.

    Parameters
    ----------
    data : pd.DataFrame
        Datos de facturas de venta. Debe contener las columnas `date`,
        `quantity`, `branch`, `is_outlier`, y la columna indicada en
        `element_column`.
    main_element : str
        Identificador del elemento a analizar (e.g. ID de producto o
        nombre de categoría).
    element_column : str
        Nombre de la columna clasificadora de elementos.
        Use `'product_id'` para productos o `'category'` para categorías.
    start_date : Date
        Fecha de inicio del período de análisis.
    end_date : Date
        Fecha de fin del período de análisis.
    include_outliers : bool
        Si es False, excluye registros marcados como atípicos.
    branch : str, optional
        Nombre de la sucursal a analizar. Si es None, se realiza análisis global.
    val : bool, optional
        Si es True, retorna también el DataFrame usado para graficar.
        Por defecto False.

    Returns
    -------
    matplotlib.figure.Figure
        Figura con el histograma de frecuencias. Se retorna cuando `val` es False.
    tuple[matplotlib.figure.Figure, pd.DataFrame]
        Tupla con la figura y el DataFrame filtrado. Se retorna cuando
        `val` es True.
     """
    def empty_fig(msg, df):
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.text(0.5, 0.5, msg, ha="center", va="center", fontsize=14)
        ax.axis("off")
        return (fig, df) if val else fig

    if data.empty or "date" not in data or element_column not in data:
        return empty_fig("No hay datos disponibles", data)
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    df = data.copy()
    filters = GraphFilters(config= GraphFilterConfig(start_date=start_date,
                                                     end_date=end_date,
                                                     element_column=element_column,
                                                     selected_elements=[main_element],
                                                     branch=branch,
                                                     include_outliers=include_outliers,
                                                     val=val))

    plot_df = filters.apply(df)
    if plot_df.empty:
        return filters.empty_plot(plot_df)

    
    fig, ax = plt.subplots(figsize=(10, 6))

    ax.hist(
        plot_df["quantity"],
        bins=100,               
        color="steelblue",
        edgecolor="black"
    )

    ax.set_title("Frecuencia de Ventas", fontsize=14, fontweight="bold")
    ax.set_xlabel("Ventas diarias")
    ax.set_ylabel("Frecuencia")
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.grid(axis="y", linestyle="--", alpha=0.7)

    fig.tight_layout()

    return (fig, plot_df) if val else fig


def prepare_sales_heatmap_data(data: pd.DataFrame,main_element: str,element_column: str,start_date,end_date,tab:str,include_outliers:bool=None,val:bool=False)->pd.DataFrame|tuple[pd.DataFrame,pd.DataFrame]:
    
    """
    Prepara y combina datos de ventas o inventario con geometrías de México
    para su uso en el mapa de calor.

    Parameters
    ----------
    data : pd.DataFrame
        Datos de ventas o inventario según el valor de `tab`. Para ventas
        debe contener `quantity` y `state`; para inventario debe contener
        `stock`, `state`, y `date`.
    main_element : str
        Identificador del elemento a analizar.
    element_column : str
        Nombre de la columna clasificadora de elementos.
    start_date : Date
        Fecha de inicio del período de análisis.
    end_date : Date
        Fecha de fin del período de análisis.
    tab : {'ventas', 'inventario'}
        Indica el tipo de datos a procesar. `'ventas'` agrega cantidades por
        estado; `'inventario'` toma el stock en la fecha de `end_date`.
    include_outliers : bool, optional
        Si es False, excluye registros atípicos. Por defecto None.
    val : bool, optional
        Si es True, retorna también el DataFrame filtrado antes del merge.
        Por defecto False.

    Returns
    -------
    geopandas.GeoDataFrame or None
        GeoDataFrame con geometrías de México y las métricas de ventas o
        inventario por estado. Retorna None si no hay datos tras el filtrado.
        Se retorna cuando `val` es False.
    tuple[geopandas.GeoDataFrame, pd.DataFrame] or None
        Tupla con el GeoDataFrame combinado y el DataFrame filtrado.
        Se retorna cuando `val` es True.
    """
    
    start_date = start_date
    end_date = end_date
    df = data.copy()
    filters = GraphFilters(config= GraphFilterConfig(start_date=start_date,
                                                     end_date=end_date,
                                                     element_column=element_column,
                                                     selected_elements=[main_element],
                                                     include_outliers=include_outliers,
                                                     val=val))

    df_filtered = filters.apply(df)
    if df_filtered.empty:
        return None
    
    mexico = load_mexico_shp()
    if tab=='ventas':

        total_sales_per_state = (
            df_filtered.groupby("state")["quantity"]
            .sum()
            .reset_index()
        )
        merged = mexico.merge(total_sales_per_state, on="state", how="left")
        merged["quantity"] = merged["quantity"].fillna(0)

    if tab=='inventario':
        mask = ( (df_filtered['date'] == end_date ))
        df_filtered = df_filtered[mask]

        total_inventory_per_state = (
            df_filtered.groupby("state")["stock"]
            .sum()
            .reset_index()
        )
        merged = mexico.merge(total_inventory_per_state, on="state", how="left")
        merged["stock"] = merged["stock"].fillna(0)
    

    return (merged,df_filtered) if val else merged



def render_sales_heat_map( merged:pd.DataFrame,
                           main_element: str,
                           tab: str,
                           map_key: str|None = None,
                           map_height: int = 300)->folium.Map | Figure :
    """
    Renderiza un mapa de calor interactivo de ventas o inventario por estado.

    Genera un mapa Folium con polígonos coloreados según la escala `Blues` de
    Matplotlib, una barra de color horizontal y tooltips con el valor por estado.

    Parameters
    ----------
    merged : pd.DataFrame or geopandas.GeoDataFrame
        Datos preparados con geometrías de México y métricas de ventas/inventario,
        generados por `prepare_sales_heatmap_data`.
    main_element : str
        Nombre del elemento visualizado, usado en el título del mapa.
    tab : {'ventas', 'inventario'}
        Indica la variable a visualizar. Determina si se usa la columna
        `'quantity'` (ventas) o `'stock'` (inventario).
    map_key : str, optional
        Identificador único del componente mapa en Streamlit. Por defecto None.
    map_height : int, optional
        Altura del mapa en píxeles. Por defecto 300.

    Returns
    -------
    folium.Map
        Mapa interactivo con los polígonos coloreados y barra de color.
        Se retorna cuando `merged` tiene datos.
    matplotlib.figure.Figure
        Figura con mensaje "No hay datos disponibles" cuando `merged` está vacío.
    """
    if merged.empty:
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.text(0.5, 0.5, "No hay datos disponibles",
                ha="center", va="center", fontsize=14)
        ax.axis("off")
        return fig

    variable = "quantity" if tab == "ventas" else "stock"

    # Mapa
    m = folium.Map(
        location=[25, -90],
        zoom_start=4,
        tiles=None,
        zoom_control=False,
        scrollWheelZoom=False,
        dragging=False,
        doubleClickZoom=False,
        touchZoom=False,
    )

    # Title
    title_html = f"""
    <h3 align="center" style="font-size:20px">
        <b>{tab.capitalize()} de {main_element} por Estado</b>
    </h3>
    """
    m.get_root().html.add_child(folium.Element(title_html))

    # Rango de valores
    vmin = merged[variable].min()
    vmax = merged[variable].max()

    # Normalizar colores
    norm = mpl.colors.Normalize(vmin=vmin, vmax=vmax)
    def rgba_to_hex(rgba):
        r, g, b, _ = rgba
        return '#{:02x}{:02x}{:02x}'.format(int(r*255), int(g*255), int(b*255))

    # Estilos de poligonos 
    def style_function(feature):
        value = feature["properties"].get(variable)
        if value is not None:
            rgba = mpl.cm.Blues(norm(value))
            fill_color = rgba_to_hex(rgba)
        else:
            fill_color = "#ffffff"
        return {
            "fillColor": fill_color,
            "color": "gray",
            "weight": 0.6,
            "fillOpacity": 0.8,
        }

    folium.GeoJson(
        merged,
        style_function=style_function,
        tooltip=folium.GeoJsonTooltip(
            fields=["NAME_1", variable],
            aliases=["Estado", tab.capitalize()],
            localize=False
        )
    ).add_to(m)

    # Barra horizontal
    fig, ax = plt.subplots(figsize=(6, 0.2))  # width x height
    cmap = mpl.cm.Blues
    mpl.colorbar.ColorbarBase(ax, cmap=cmap, norm=norm, orientation='horizontal')
    ax.set_xticks([vmin, (vmin+vmax)/2, vmax])
    ax.set_yticks([])

    # Guardar a png en memoria
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', dpi=150)
    plt.close(fig)
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    img_html = f'<img src="data:image/png;base64,{img_base64}" style="width:100%;">'

    colorbar_div = f"""
    <div style="
        position: absolute;
        top: 10px;         /* distance from top */
        left: 50px;        /* horizontal offset */
        width: 300px;      /* width of colorbar */
        height: 30px;
        z-index: 9999;
        background-color: transparent;
    ">
        {img_html}
    </div>
    """
    m.get_root().html.add_child(folium.Element(colorbar_div))
    map_data = st_folium(m, width=700, height=map_height, key=map_key)

    

    return m

def abc_bar_chart(data:pd.DataFrame,element_column:str,start_date:Date,end_date:Date,branch:str,include_outliers:bool,val:bool=False)->Figure|tuple[Figure,pd.DataFrame]:
    """
    Genera un gráfico de barras horizontales con clasificación ABC de
    productos o categorías por valor de ventas.

    Clasifica cada elemento en prioridad Alta, Media o Baja según su
    porcentaje de aportación acumulada al valor total de ventas del período.
    Se muestran los 20 elementos con mayor volumen de ventas.

    Parameters
    ----------
    data : pd.DataFrame
        Datos de facturas de venta. Debe contener las columnas `date`,
        `quantity`, `cost`, `branch`, `is_outlier`, y la columna indicada
        en `element_column`.
    element_column : str
        Nombre de la columna clasificadora de elementos.
        Use `'product_id'` para productos o `'category'` para categorías.
    start_date : Date
        Fecha de inicio del período de análisis.
    end_date : Date
        Fecha de fin del período de análisis.
    branch : str
        Nombre de la sucursal a analizar.
    include_outliers : bool
        Si es False, excluye registros marcados como atípicos.
    val : bool, optional
        Si es True, retorna también el DataFrame usado para graficar.
        Por defecto False.

    Returns
    -------
    matplotlib.figure.Figure
        Figura con el gráfico de barras y leyenda de prioridades ABC.
        Se retorna cuando `val` es False.
    tuple[matplotlib.figure.Figure, pd.DataFrame]
        Tupla con la figura y el DataFrame con columnas `element_column`,
        `total_sales`, `annual_value`, `cumulative_val` y `prioridad`.
        Se retorna cuando `val` es True.

    Notes
    -----
    La clasificación ABC se define como:

    - **Alta** : aportación acumulada <= 80 % del valor total.
    - **Media**: aportación acumulada entre 80 % y 95 %.
    - **Baja** : aportación acumulada > 95 %.

    El valor anual de cada elemento se calcula como
    ``total_sales * min_cost``.
    """
    
    def abc_class(x):
        if x <= 0.80:
            return "Alta"
        elif x <= 0.95:
            return "Media"
        else:
            return "Baja"
        
    # Filtros

    type_selected = element_column
    start_date = pd.to_datetime(start_date)
    end_date   = pd.to_datetime(end_date)
    df = data.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    
    filters = GraphFilters(config= GraphFilterConfig(start_date=start_date,
                                                     end_date=end_date,
                                                     branch=branch,
                                                     include_outliers=include_outliers,
                                                     val=val))

    df_filtered = filters.apply(df)
    if df_filtered.empty:
        return filters.empty_plot(df_filtered)


    df_summary = (
        df_filtered
            .groupby([type_selected],as_index=False)
            .agg(
                total_sales=("quantity", "sum"),
                min_cost=("cost", "min")  
            )
    )

    df_summary["annual_value"] = df_summary["total_sales"] * df_summary["min_cost"]
    df_summary = df_summary.sort_values("annual_value", ascending=False)
    df_summary["cumulative_val"] = df_summary["annual_value"].cumsum() / df_summary["annual_value"].sum()
    df_summary["prioridad"] = df_summary["cumulative_val"].apply(abc_class)



    color_map = {"Alta":"red", "Media":"blue", "Baja":"gray"}

    plot_df = df_summary.sort_values(by="total_sales",ascending=False)
    plot_df = plot_df.reset_index()[:20]


    fig, ax = plt.subplots(figsize=(10, 8))

    # Barras
    ax.barh(
        plot_df[type_selected],
        plot_df["total_sales"],
        color=plot_df["prioridad"].map(color_map)
    )
    if element_column=='category':
        element='Categoría'
    else:
        element='Producto'    
        
    ax.set_xlabel("Ventas Totales")
    ax.set_title(f"Ventas Totales en {branch.capitalize()} por {element} ")

    # Mostrar valores sobre las barras
    max_val = plot_df["total_sales"].max()
    for i, v in enumerate(plot_df["total_sales"]):
        ax.text(v + max_val * 0.01, i, str(v), va='center')

    # Leyenda
    patches = [mpatches.Patch(color=color, label=cls) for cls, color in color_map.items()]
    ax.legend(handles=patches, title="Prioridad")

    # Invertir eje y
    ax.invert_yaxis()

    fig.tight_layout()
    
    if val:
        return fig,plot_df
    
    
    return fig


