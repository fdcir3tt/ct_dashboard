import pandas as pd
import geopandas as gpd
import numpy as np
import folium
import warnings
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.patches as mpatches


from ct_sales_dashboard.utils import time_period,month_dict
from streamlit_folium import st_folium
from matplotlib.ticker import MaxNLocator
from matplotlib.figure import Figure

warnings.filterwarnings('ignore')


def load_mexico_shp():
    mexico = gpd.read_file("data/raw/gadm41_MEX_shp/gadm41_MEX_1.shp")
    mexico["geometry"] = mexico["geometry"].simplify(
        tolerance=0.01, preserve_topology=True
    )
    mexico["state"] = mexico["NAME_1"].str.upper()
    return mexico


# -----------------------------------------------------------
# GRÄFICAS
# -----------------------------------------------------------

def period_sales(data: pd.DataFrame, 
                 selected_elements: list[str] ,
                 element_column:str ,
                 start_date, end_date,
                 include_outliers:bool=None,
                 branch:str=None,
                 val:bool=False,**kwargs)->Figure:
    """
    Grafica curva de ventas y regresa la figura.
    """

    # --- Validaciones básicas ---
    if data.empty:
        
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.text(0.5, 0.5, "No hay datos disponibles", ha="center", va="center", fontsize=14)
        ax.axis("off")
        return (fig, data) if val else fig

    if "date" not in data or element_column not in data:
        
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.text(0.5, 0.5, "No se encuentran datos de fecha o del producto", ha="center", va="center", fontsize=14)
        ax.axis("off")
        #fig.savefig("plots/almacen_ventas.png")
        return (fig, data) if val else fig
    

    # --- Asegurar que las fechas SON datetime ---
    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    data["month"] = data["date"].dt.month
    data["year"] = data["date"].dt.year

    start_date = pd.to_datetime(start_date)
    end_date   = pd.to_datetime(end_date)

    df = data.copy()
    # Filtro por rango de fechas
    in_period = (df['date'] >= start_date) & (df['date'] <= end_date)
    # Filtro por productos o categorías
    in_selected = df[element_column].isin(selected_elements)
    

    mask = in_period & in_selected
    if not include_outliers:
        mask &= df["is_outlier"] == include_outliers

    df = df[mask]

    if df.empty:
        
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.text(0.5, 0.5, "No hay datos disponibles", ha="center", va="center", fontsize=14)
        ax.axis("off")
        return (fig, df) if val else fig
    
    # Filtro por sucursal 
    if branch:
        in_branch = df["sucursal"]==branch
        df = df[in_branch]

    if df.empty:
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.text(0.5, 0.5, "No hay datos disponibles", ha="center", va="center", fontsize=14)
        ax.axis("off")
        return (fig, df) if val else fig
    
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

def period_inventory(data: pd.DataFrame,
                     branch_storage:dict[str,list[str]], 
                     selected_elements: list[str] ,
                     element_column:str ,
                     start_date, end_date,
                     branch:str=None,
                     val:bool=False,**kwargs)->Figure:
    """
    Grafica curva de inventario y regresa la figura.
    """
    
    # --- Validaciones básicas ---
    if data.empty or (not branch_storage):
        
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.text(0.5, 0.5, "No hay datos disponibles", ha="center", va="center", fontsize=14)
        ax.axis("off")
        return (fig, data) if val else fig

    if "date" not in data or element_column not in data:
        
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.text(0.5, 0.5, "No se encuentran datos de fecha o del producto", ha="center", va="center", fontsize=14)
        ax.axis("off")
        #fig.savefig("plots/almacen_ventas.png")
        return (fig, data) if val else fig
    

    # --- Asegurar que las fechas SON datetime ---
    data["date"] = pd.to_datetime(data["date"], errors="coerce")

    start_date = pd.to_datetime(start_date)
    end_date   = pd.to_datetime(end_date)

    df = data.copy().reset_index(drop=True)
    mask = ((df['date'] >= start_date) & (df['date'] <= end_date) & 
             df[element_column].isin(selected_elements))

    df = df[mask]

    if df.empty:
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.text(0.5, 0.5, "No hay datos disponibles", ha="center", va="center", fontsize=14)
        ax.axis("off")
        return (fig, df) if val else fig
    
    if branch:
        storages = branch_storage[branch]
        mask &= df['storage_id'].isin(storages)
    else:
        storages = []
        for b in branch_storage.values():
            storages+=b

        mask &= df['storage_id'].isin(storages)

    df = df[mask] 

    period = pd.DataFrame(data=time_period(start_date=start_date,end_date=end_date ),
                          columns=["date"])
    period = period.assign(key=1)
    storages_df = pd.DataFrame({'storage_id': storages})
    storages_df['key'] = 1
    period = period.merge(storages_df, on='key').drop('key', axis=1)
    
    period = period.explode('storage_id')

    df = period.merge(right=df,how='left',on=['date','storage_id'])
    df['stock'] = df['stock'].fillna(value=0)
    df['total_stock']= df.groupby(['date'])['stock'].transform('sum')
    

    df["month"] = df["date"].dt.month
    df["year"] = df["date"].dt.year
    month = month_dict[ df["month"].iloc[0] ]
    year = df["year"].iloc[0]
    
    
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

def sales_velocity(data:pd.DataFrame,
                   selected_elements:list,
                   element_column: str,
                   branch:str,
                   start_date,end_date,
                   outliers:bool=None,
                   val:bool=False,**kwargs):
    
    if data.empty:
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.text(0.5, 0.5, "No hay datos disponibles", ha="center", va="center", fontsize=14)
        ax.axis("off")
        return (fig, data) if val else fig

    if "date" not in data or element_column not in data:
        
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.text(0.5, 0.5, "No se encuentran datos de fecha o del producto", ha="center", va="center", fontsize=14)
        ax.axis("off")
        return (fig, data) if val else fig
    
    df = data.copy()

    df['sales_velocity'] = (
    df['sales_day']
        .rolling(window=2)
        .mean()
        .interpolate(method="linear", limit_direction="both")
)

    df['date'] = pd.to_datetime(df['date'], errors='coerce')

    
    start_date = pd.to_datetime(start_date)
    end_date   = pd.to_datetime(end_date)


    in_period = ( start_date <= df['date'] ) & ( df['date'] <= end_date )
    # Filtro por productos o categorías
    in_selected = data[element_column].isin(selected_elements)

    # Filtro por sucursal 
    in_branch = df["sucursal"]==branch
    
    
    mask = in_period & in_selected & in_branch
    if outliers:
        mask &= df["is_outlier"] == outliers
    df = df[mask]
    

    if df.empty:
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.text(0.5, 0.5, "No hay datos disponibles", ha="center", va="center", fontsize=14)
        ax.axis("off")
        return (fig, df) if val else fig
    
    month = month_dict[ df["month"].iloc[0] ]
    year = df["year"].iloc[0]
    
    
    # Líneas interpoladas
    
        
    fig, ax = plt.subplots(figsize=(12, 6))
    plt.style.use("seaborn-v0_8")
    
    colors = ["#e63947","#39e6c9","#0400ff","#e43d0a"]
    no_data_color = "#ee08db"
    i = 0
    for id in selected_elements:
        is_element = df[element_column]==id
        plot_df = df[is_element]
        if plot_df.empty:
            ax.plot(plot_df["date"], plot_df["sales_velocity"], label= id+" (no hay datos)",
                marker="o", color=no_data_color)
            continue
        ax.plot(plot_df["date"], plot_df["sales_velocity"], label= id,
                marker="o", color=colors[i])
        
    # === Recta de tendencia === #
        # Convertir fechas a valores numéricos (ordinales)
        
        x = mdates.date2num(plot_df["date"])
        y = plot_df["sales_velocity"]

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





    # Título y etiquetas
    ax.set_title("Rápidez de Ventas (ventas/día)", fontsize=16, fontweight="bold")
    ax.set_xlabel("Fecha")
    ax.set_ylabel("Rápidez (cantidad/día)")
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))

   
    # Eje X limpio
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    fig.autofmt_xdate(rotation=45, ha="right")  

    
    ax.grid(False)
    ax.legend()
    fig.tight_layout()
    
    return (fig, plot_df) if val else fig


def sales_hist(data: pd.DataFrame,
               main_element: str,
               element_column: str,
               start_date,end_date,
               include_outliers:bool,
               branch: str = None,
               val: bool = False,):
    """
    Función que recibe el dataframe de datos del periodo especificado y 
    gráfica las curvas de existencia del producto y ventas.
    """
    def empty_fig(msg, df):
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.text(0.5, 0.5, msg, ha="center", va="center", fontsize=14)
        ax.axis("off")
        return (fig, df) if val else fig

    if data.empty or "date" not in data or element_column not in data:
        return empty_fig("No hay datos disponibles", data)

    df = data.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    mask = (
        (df["date"] >= pd.to_datetime(start_date)) &
        (df["date"] <= pd.to_datetime(end_date)) &
        (df[element_column] == main_element)
    )

    if branch:
        mask &= df["sucursal"] == branch
    if not include_outliers:
        mask &= df["is_outlier"] == include_outliers

    df = df.loc[mask, ["quantity"]].dropna()

    if df.empty:
        return empty_fig("No hay datos disponibles", df)

    
    fig, ax = plt.subplots(figsize=(10, 6))

    ax.hist(
        df["quantity"],
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

    return (fig, df) if val else fig


def prepare_sales_heatmap_data(data: pd.DataFrame, 
                               main_element: str,
                               element_column: str,
                               start_date,end_date,
                               include_outliers:bool=None,
                               val:bool=False,**kwargs)->pd.DataFrame:
    
    if data.empty or "date" not in data or element_column not in data:
        return None

    df = data.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    mask = (
        (df["date"] >= pd.to_datetime(start_date)) &
        (df["date"] <= pd.to_datetime(end_date)) &
        (df[element_column] == main_element )
    )

    if not include_outliers:
        mask &= df["is_outlier"] == include_outliers

    df_filtered = df[mask]

    if df_filtered.empty:
        return None

    total_sales_per_state = (
        df_filtered.groupby("state")["quantity"]
        .sum()
        .reset_index()
    )

    mexico = load_mexico_shp()
    merged = mexico.merge(total_sales_per_state, on="state", how="left")
    merged["quantity"] = merged["quantity"].fillna(0)

    return (merged,df_filtered) if val else merged

def render_sales_heat_map(merged: pd.DataFrame,
                          main_element: str,
                          map_key:str=None)->tuple[folium.Map,str]:
    if merged is None:
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.text(0.5, 0.5, "No hay datos disponibles", ha="center", va="center", fontsize=14)
        ax.axis("off")
        return fig, None

    m = folium.Map(
        location=[20, -90],
        tiles=None,
        zoom_start=4,
        zoom_control=True,
        scrollWheelZoom=True,
        dragging=True,
        doubleClickZoom=False,
        touchZoom=False,
    )

    title_html = f"""
    <h3 align="center" style="font-size:20px">
        <b>Ventas de {main_element} por Estado</b>
    </h3>
    """
    m.get_root().html.add_child(folium.Element(title_html))

    folium.Choropleth(
        geo_data=merged,
        data=merged,
        columns=["state", "quantity"],
        key_on="feature.properties.state",
        fill_color="Blues",
        fill_opacity=0.8,
        line_opacity=0,
        nan_fill_color="white",
        legend_name="Ventas",
    ).add_to(m)

    folium.GeoJson(
        merged,
        tooltip=folium.GeoJsonTooltip(
            fields=["NAME_1", "quantity"],
            aliases=["Estado", "Ventas"],
        ),
        name="Estados",
        style_function=lambda x: {
            "color": "gray",
            "weight": 0.5,
            "fillOpacity": 0,
        },
    ).add_to(m)

    map_data = st_folium(m, width=700, height=250,key=map_key)

    selected_state = None
    if map_data and "last_active_drawing" in map_data:
        props = map_data["last_active_drawing"]
        if props and "properties" in props:
            selected_state = props["properties"].get("NAME_1")

    return m, selected_state



def abc_bar_chart(data:pd.DataFrame,
                  start_date:str,
                  end_date:str,
                  branch:str,
                  include_outliers:bool,
                  type:str="productos",
                  val:bool=False,**kwargs):
    
    if data.empty:
        print("Dataset vacío")
        return None
    type_dict={"productos":"productId","categorias":"category"}
    def abc_class(x):
        if x <= 0.80:
            return "Alta"
        elif x <= 0.95:
            return "Media"
        else:
            return "Baja"
        
    # Filtros

    type_selected = type_dict[type]
    start_date = pd.to_datetime(start_date)
    end_date   = pd.to_datetime(end_date)

    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    df = data.copy()

    is_in_period = ( start_date <= df["date"] ) & ( df["date"] <= end_date )
    in_branch = df["sucursal"] == branch

    mask = is_in_period&in_branch
    if not include_outliers:
        mask &= df["is_outlier"] == include_outliers

    df_filtered = df[mask]


    df_summary = (
        df_filtered
            .groupby([type_selected,"sucursal"],as_index=False)
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

    df_plot = df_summary.sort_values(by="total_sales",ascending=False)
    df_plot = df_plot.reset_index()[:20]


    fig, ax = plt.subplots(figsize=(10, 8))

    # Barras
    ax.barh(
        df_plot[type_selected],
        df_plot["total_sales"],
        color=df_plot["prioridad"].map(color_map)
    )

    ax.set_xlabel("Ventas Totales")
    ax.set_title(f"Ventas Totales en Sucursal por {type[:-1].capitalize()} ")

    # Mostrar valores sobre las barras
    max_val = df_plot["total_sales"].max()
    for i, v in enumerate(df_plot["total_sales"]):
        ax.text(v + max_val * 0.01, i, str(v), va='center')

    # Leyenda
    patches = [mpatches.Patch(color=color, label=cls) for cls, color in color_map.items()]
    ax.legend(handles=patches, title="Prioridad")

    # Invertir eje y
    ax.invert_yaxis()

    fig.tight_layout()
    if val:
        return fig,df_summary
    
    
    return fig


