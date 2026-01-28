import pandas as pd
import geopandas as gpd
import numpy as np
import folium
import streamlit as st
from streamlit_folium import st_folium
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.patches as mpatches
from matplotlib.ticker import MaxNLocator
from matplotlib.figure import Figure

@st.cache_resource
def load_mexico_shp():
    mexico = gpd.read_file("data/raw/gadm41_MEX_shp/gadm41_MEX_1.shp")
    mexico["geometry"] = mexico["geometry"].simplify(
        tolerance=0.01, preserve_topology=True
    )
    mexico["state"] = mexico["NAME_1"].str.upper()
    return mexico


month_dict={  1:"Enero",
                  2:"Febrero",
                  3:"Marzo",
                  4:"Abril",
                  5:"Mayo",
                  6:"Junio",
                  7:"Julio",
                  8:"Agosto",
                  9:"Septiembre",
                  10:"Octubre",
                  11:"Noviembre",
                  12:"Diciembre"}
# -----------------------------------------------------------
# AUXILIARES
# -----------------------------------------------------------

def remove_outliers(data: pd.DataFrame, column: str) -> pd.DataFrame:
    series = data[column]
    
    Q1 = series.quantile(0.25)
    Q3 = series.quantile(0.75)
    IQR = Q3 - Q1
    lower = Q1 - 1.5 * IQR
    upper = Q3 + 1.5 * IQR
    
    clean_data = data[(series >= lower) & (series <= upper)]
    return clean_data


def top_n(data:pd.DataFrame,element_column,type:str="producto",criteria:str="ventas_diarias",n:int=5)->list[str]:
    """
    Recibe el dataframe de datos del periodo especificado y regresa los mejores
    'n' productos o categorías en base el criterio específicado.
    """
    type_dict= {"producto":"productId",
                "categoria":"category",
                "sucursal":"branchId",
                "cliente":"clientId"}

    criteria_dict={"ventas_diarias":"sales_day",
                   "ventas_mensuales":"sales_month",
                   "ganancia_total":"total_profit"}
    
    data["sales_day"] = data.groupby([element_column, "date"])["quantity"].transform("sum")
    if n==1:
        top_n= data[[type_dict[type],criteria_dict[criteria]]].sort_values(by=criteria_dict[criteria],ascending=False)[type_dict[type]].iloc[0]
        return top_n
    if n<0 :
        df= data[[type_dict[type],criteria_dict[criteria]]].sort_values(by=criteria_dict[criteria],ascending=True).drop_duplicates()[:abs(n)]
        return df
    df= data[[type_dict[type],criteria_dict[criteria]]].sort_values(by=criteria_dict[criteria],ascending=False).drop_duplicates()[:n]

    top_n= df

    return top_n

def frequency(data:pd.DataFrame,type:str="cliente")->pd.DataFrame:
    """
    Recibe el dataframe de datos del periodo especificado y regresa los ritmos de ventas promedio
    en dicho periodo. 

    """
    if data.empty:
        print("Dataset vacío")
        return None
    type_dict= {"producto":"productId",
                "categoria":"category",
                "sucursal":"branch",
                "cliente":"client",
                "dia":"weekday",
                "mes":"month"}
    
    column = type_dict[type]
    data["date"] = pd.to_datetime(data["date"])
    start = data["date"].min().day
    end = data["date"].max().day

    period_length = end - start
    df = data[[column,"date"]].value_counts().to_frame("count")
    df["total"] = df.groupby(level=column)["count"].transform("sum") 
    df["avg_rate"] = df["total"]/period_length
    df = df.reset_index()
    df = df[[column,"avg_rate"]].drop_duplicates().reset_index().drop(columns="index")
    return df

def frequent_clients(data:pd.DataFrame,level:str="producto",n:int=5)->list[str]:
    level_dict={"producto":"productId"}
    df = frequency(data)
    df = df.sort_values(by="avg_rate",ascending=False)
    frequent_clients = list( df[:n])
    return frequent_clients

def top_day(data:pd.DataFrame)->str:
    weekday_dict={0:"Lunes",
                  1:"Martes",
                  2:"Miercoles",
                  3:"Jueves",
                  4:"Viernes",
                  5:"Sábado",
                  6:"Domingo"}
    
    data["date"] = pd.to_datetime(data["date"])
    data["weekday"]=data["date"].dt.weekday
    df = frequency(data,type="dia")
    df = df.sort_values(by="avg_rate",ascending=False)
    return weekday_dict[df["weekday"].iloc[0]]

def top_month(data:pd.DataFrame)->str:

    
    data["date"] = pd.to_datetime(data["date"])
    
    df = frequency(data,type="mes")
    df = df.sort_values(by="avg_rate",ascending=False)
    return month_dict[df["month"].iloc[0]]

# -----------------------------------------------------------
# GRÄFICAS
# -----------------------------------------------------------

def period_sales(data: pd.DataFrame, selected_elements: list[str] ,element_column:str ,start_date, end_date,branch:str=None,val:bool=False,**kwargs)->Figure:
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

    # Filtro por rango de fechas
    in_period = (data["date"] >= start_date) & (data["date"] <= end_date)
    data = data[in_period]

    # Filtro por productos o categorías
    in_selected = data[element_column].isin(selected_elements)
    df = data[in_selected].copy()

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

def period_inventory(data: pd.DataFrame,branch_storage:dict[str], selected_elements: list[str] ,element_column:str ,start_date, end_date,branch:str=None,val:bool=False,**kwargs)->Figure:
    """
    Grafica curva de inventario y regresa la figura.
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

    start_date = pd.to_datetime(start_date)
    end_date   = pd.to_datetime(end_date)

    # Filtro por rango de fechas
    in_period = (data["date"] >= start_date) & (data["date"] <= end_date)
    data = data[in_period]

    # Filtro por productos o categorías
    in_selected = data[element_column].isin(selected_elements)
    df = data[in_selected].copy()

    if df.empty:
        
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.text(0.5, 0.5, "No hay datos disponibles", ha="center", va="center", fontsize=14)
        ax.axis("off")
        return (fig, df) if val else fig
    
    
    # Inventario por sucursal
    if branch:
        storages = branch_storage[branch] 
        df["stock"] = 0
        for s in storages:
            df["stock"] = df["existence"].apply(lambda x: sum(x[s] for s in storages if isinstance(x, dict) and s in x))
    else:
        df["stock"] = df["existence"].apply(lambda x: sum(x.values()))

    if df.empty:
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.text(0.5, 0.5, "No hay datos disponibles", ha="center", va="center", fontsize=14)
        ax.axis("off")
        return (fig, df) if val else fig
    
    df["month"] = df["date"].dt.month
    df["year"] = df["date"].dt.year

    month = month_dict[ df["month"].iloc[0] ]
    year = df["year"].iloc[0]
    
    
    # Líneas interpoladas
    df["stock"] = df["stock"].interpolate(method="linear")
    
        
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
        ax.plot(plot_df["date"], plot_df["stock"], label= id,
                marker="o", color=colors[i])
        
    # === Recta de tendencia === #

    # Convertir fechas a valores numéricos (ordinales)
        
        x = mdates.date2num(plot_df["date"])
        y = plot_df["stock"]

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

def sales_velocity(data:pd.DataFrame,selected_elements:list,element_column: str,branch:str,start_date,end_date,val:bool=False,**kwargs):
    
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
    

    data["sales_velocity"] = (
    data["sales_day"]
        .rolling(window=2)
        .mean()
        .interpolate(method="linear", limit_direction="both")
)

    data["date"] = pd.to_datetime(data["date"], errors="coerce")

    
    start_date = pd.to_datetime(start_date)
    end_date   = pd.to_datetime(end_date)
    is_in_period = ( start_date <= data["date"] ) & ( data["date"] <= end_date )
    data = data[is_in_period]


    # Filtro por productos o categorías
    in_selected = data[element_column].isin(selected_elements)
    df = data[in_selected].copy()

    if df.empty:
        
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.text(0.5, 0.5, "No hay datos disponibles", ha="center", va="center", fontsize=14)
        ax.axis("off")
        return (fig, df) if val else fig

    # Filtro por sucursal 
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


def sales_hist(data: pd.DataFrame,main_element: str,element_column: str,start_date,end_date,branch: str = None,val: bool = False,):
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

    data = data.copy()
    data["date"] = pd.to_datetime(data["date"], errors="coerce")

    mask = (
        (data["date"] >= pd.to_datetime(start_date)) &
        (data["date"] <= pd.to_datetime(end_date)) &
        (data[element_column] == main_element)
    )

    if branch:
        mask &= data["sucursal"] == branch

    df = data.loc[mask, ["quantity"]].dropna()

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


@st.cache_data
def prepare_sales_heatmap_data(data: pd.DataFrame, main_element: str,element_column: str,start_date,end_date,val:bool=False,**kwargs)->pd.DataFrame:
    if data.empty or "date" not in data or element_column not in data:
        return None

    data = data.copy()
    data["date"] = pd.to_datetime(data["date"], errors="coerce")

    data = data[
        (data["date"] >= pd.to_datetime(start_date)) &
        (data["date"] <= pd.to_datetime(end_date))
    ]

    df_filtered = data[data[element_column] == main_element]

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

def render_sales_heat_map(merged: pd.DataFrame, main_element: str,map_key:str=None)->tuple[folium.Map,str]:
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



def abc_bar_chart(data:pd.DataFrame,start_date:str,end_date:str,branch:str,type:str="productos",val:bool=False,**kwargs):
    
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

    is_in_period = ( start_date <= data["date"] ) & ( data["date"] <= end_date )
    in_branch = data["sucursal"] == branch
    df_filtered = data[is_in_period&in_branch]


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


