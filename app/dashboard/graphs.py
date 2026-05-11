import pandas as pd
import geopandas as gpd
import numpy as np
import folium
import branca.colormap as cm
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
    start_date: date
    end_date: date
    element_column: str | None = None
    selected_elements: list | None = None
    branch: str | None = None
    include_outliers: bool | None= None
    val: bool = False

class GraphFilters:
    def __init__(self, config: GraphFilterConfig):
        self.cfg = config

    def apply(self, data: pd.DataFrame):
        
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

        if df.empty:
            fig, ax = plt.subplots(figsize=(8, 4))
            ax.text(0.5, 0.5, "No hay datos disponibles",
                    ha="center", va="center", fontsize=14)
            ax.axis("off")

            return (fig, df) if self.cfg.val else fig

def load_mexico_shp():
    """
    Carga archivos 'shp' necesarios de México para mapa de calor
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
    Grafica curva de ventas.

    Parametros:
    - data: pandas.DataFrame, Datos de facturas de venta 
    - selected_elements: list[str] , Elementos seleccionados a visualizar en gráfica .(ej. Productos o Categorías de producto)
    - element_column: str, Nombre de columna clasificadora de elementos. Es decir 'productId' para productos o 'category' para categoría de producto
    - start_date: Date, Fecha inicio de periodo de análisis
    - end_date: Date, Fecha fin de periodo de análisis
    - include_outliers: bool, Booleano para afirmar la inclusión de ventas atípicas en el análisis
    - branch: str, Nombre de sucursal en cual se quiere hacer análisis. Si es análisis global, no se incluye.
    - val: bool, Paramétro para pruebas unitarias de función

    Regresa:
    - fig: matplotlib.figure.Figure , Figura de gráfico 
    - plot_df: pandas.DataFrame, Datos usados para la visualización de ventas

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
    df["sales_day"] = df["sales_day"].interpolate(method="linear")
    
        
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
        ax.plot(plot_df["date"], plot_df["sales_day"], label= id,
                marker="o", color=colors[i])
        
    # === Recta de tendencia === #

    # Convertir fechas a valores numéricos (ordinales)
        
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
    Grafica curva de inventario.

    Parametros:
    - data: pandas.DataFrame, Datos de facturas de venta 
    - branch_storage: dict[str,list[str]], Diccionario que contiene los almacenes asociados a cada sucursal.
    - selected_elements: list[str] , Elementos seleccionados a visualizar en gráfica .(ej. Productos o Categorías de producto)
    - element_column: str, Nombre de columna clasificadora de elementos. Es decir 'productId' para productos o 'category' para categoría de producto
    - start_date: Date, Fecha inicio de periodo de análisis
    - end_date: Date, Fecha fin de periodo de análisis
    - branch: str, Nombre de sucursal en cual se quiere hacer análisis. Si es análisis global, no se incluye.
    - val: bool, Paramétro para pruebas unitarias de función

    Regresa:
    - fig: matplotlib.figure.Figure , Figura de gráfico 
    - plot_df: pandas.DataFrame, Datos usados para la visualización de existencias

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
            storages = list(branch_storage[branch_storage["branch"]==branch]["storageId"].unique())
        mask = df['storageId'].isin(storages)
    else:
        if isinstance(branch_storage,dict):
            storages = []
            for b in branch_storage.values():
                storages+=b

        elif isinstance(branch_storage,pd.DataFrame):
            storages = list(branch_storage["storageId"].unique())

        mask = df['storageId'].isin(storages)

    df=df[mask]
    df['total_stock']= df.groupby(['date',element_column])['stock'].transform('sum')
    

    
    
    # Líneas interpoladas
    df["total_stock"] = df["total_stock"].interpolate(method="linear")
    
        
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
        ax.plot(plot_df["date"], plot_df["total_stock"], label= id,
                marker="o", color=colors[i])
        
    # === Recta de tendencia === #

    # Convertir fechas a valores numéricos (ordinales)
        
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
    Gráfica frecuencias de venta.

    Parametros:
    - data: pandas.DataFrame, Datos de facturas de venta     
    - main_element: str , Elemento seleccionado a visualizar en gráfica .(ej. Producto o Categoría de producto)
    - element_column: str, Nombre de columna clasificadora de elementos. Es decir 'productId' para productos o 'category' para categoría de producto
    - start_date: Date, Fecha inicio de periodo de análisis
    - end_date: Date, Fecha fin de periodo de análisis
    - include_outliers: bool, Booleano para afirmar la inclusión de ventas atípicas en el análisis
    - branch: str, Nombre de sucursal en cual se quiere hacer análisis. Si es análisis global, no se incluye.
    - val: bool, Paramétro para pruebas unitarias de función

    Regresa:
    - fig: matplotlib.figure.Figure , Figura de gráfico 
    - plot_df: pandas.DataFrame, Datos usados para la visualización de frecuencias

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
    Prepara datos para gráfica mapa de calor uniendo datos geoespaciales de México y datos de ventas/inventario.

    Parametros:
    - data: pandas.DataFrame, Datos de facturas de venta o datos de inventario    
    - main_element: str , Elemento seleccionado a visualizar en gráfica .(ej. Producto o Categoría de producto)
    - element_column: str, Nombre de columna clasificadora de elementos. Es decir 'productId' para productos o 'category' para categoría de producto
    - start_date: Date, Fecha inicio de periodo de análisis
    - end_date: Date, Fecha fin de periodo de análisis
    - tab: str, Indica si se trabajara con datos de inventario o de ventas
    - include_outliers: bool, Booleano para afirmar la inclusión de ventas atípicas en el análisis
    - branch: str, Nombre de sucursal en cual se quiere hacer análisis. Si es análisis global, no se incluye.
    - val: bool, Paramétro para pruebas unitarias de función

    Regresa:
    - merged: pandas.DataFrame , Datos usados para la visualización de ventas/inventario en mapa de calor
    - filtered_df: pandas.DataFrame, Datos filtrados antes de unirse con los datos geométricos de México

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
        mask = ( (df_filtered['date'] == pd.to_datetime(end_date) ))
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
    Gráfica mapa de calor de ventas/inventario.

    Parametros:
    - merged: pandas.DataFrame, Datos preparados  
    - main_element: str , Elemento seleccionado a visualizar en gráfica .(ej. Producto o Categoría de producto)
    - tab: str, Indica si se trabajara con datos de inventario o de ventas
    - map_key: str, Identificador de objeto mapa
    - map_height: int, Paramétro para configurar altura de mapa en pixeles

    Regresa:
    - m: folium.Map , Mapa de calor a visualizar
    - fig: matplotlib.figure.Figure, Figura en caso de que no hayan datos a visualizar

    """
    if merged is None:
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
    Gráfica prioridades de producto/categoría. Clasifica prioridad de producto/categoría en base 
    porcentaje de aportación a valor adquirido en periodo especificado. El valor adquirido se cal-
    cula con el costo total de las ventas realizadas. 

    Parametros:
    - data: pandas.DataFrame, Datos de facturas de venta     
    - element_column: str, Nombre de columna clasificadora de elementos. Es decir 'productId' para productos o 'category' para categoría de producto
    - start_date: Date, Fecha inicio de periodo de análisis
    - end_date: Date, Fecha fin de periodo de análisis
    - include_outliers: bool, Booleano para afirmar la inclusión de ventas atípicas en el análisis
    - branch: str, Nombre de sucursal en cual se quiere hacer análisis. Si es análisis global, no se incluye.
    - val: bool, Paramétro para pruebas unitarias de función

    Regresa:
    - fig: matplotlib.figure.Figure , Figura de gráfico 
    - plot_df: pandas.DataFrame, Datos usados para la visualización de prioridades

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


