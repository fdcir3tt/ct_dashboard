import pandas as pd
import geopandas as gpd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.patches as mpatches
from matplotlib.ticker import MaxNLocator


def remove_outliers(data: pd.DataFrame, column: str) -> pd.DataFrame:
    series = data[column]
    
    Q1 = series.quantile(0.25)
    Q3 = series.quantile(0.75)
    IQR = Q3 - Q1
    lower = Q1 - 1.5 * IQR
    upper = Q3 + 1.5 * IQR
    
    clean_data = data[(series >= lower) & (series <= upper)]
    return clean_data


def top_n(data:pd.DataFrame,type:str="producto",criteria:str="ventas_diarias",n:int=5)->list[str]:
    """
    Recibe el dataframe de datos del periodo especificado y regresa los mejores
    'n' productos o categorías en base el criterio específicado.
    """
    type_dict= {"producto":"productId",
                "categoria":"category",
                "sucursal":"branch",
                "cliente":"client"}

    criteria_dict={"ventas_diarias":"sales_day",
                   "ventas_mensuales":"sales_month",
                   "ganancia_total":"total_profit"}
    
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
    data["fecha"] = pd.to_datetime(data["fecha"])
    start = data["fecha"].min().day
    end = data["fecha"].max().day

    period_length = end - start
    df = data[[column,"fecha"]].value_counts().to_frame("count")
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
    
    data["fecha"] = pd.to_datetime(data["fecha"])
    data["weekday"]=data["fecha"].dt.weekday
    df = frequency(data,type="dia")
    df = df.sort_values(by="avg_rate",ascending=False)
    return weekday_dict[df["weekday"].iloc[0]]

def top_month(data:pd.DataFrame)->str:
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
    
    data["fecha"] = pd.to_datetime(data["fecha"])
    
    df = frequency(data,type="mes")
    df = df.sort_values(by="avg_rate",ascending=False)
    return month_dict[df["month"].iloc[0]]

def period_sales(data: pd.DataFrame, selected_elements: list[str] ,element_column:str, start_date, end_date):
    """
    Grafica curva de ventas y regresa la figura.
    """
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
    


    # --- Validaciones básicas ---
    if data.empty:
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.text(0.5, 0.5, "No hay datos disponibles", ha="center", va="center", fontsize=14)
        ax.axis("off")
        return fig

    if "fecha" not in data or element_column not in data:
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.text(0.5, 0.5, "No se encuentran datos de fecha o del producto", ha="center", va="center", fontsize=14)
        ax.axis("off")
        fig.savefig("plots/almacen_ventas.png")
        return fig

    # --- Asegurar que las fechas SON datetime ---
    data["fecha"] = pd.to_datetime(data["fecha"], errors="coerce")

    start_date = pd.to_datetime(start_date)
    end_date   = pd.to_datetime(end_date)

    # Filtro por rango de fechas
    in_period = (data["fecha"] >= start_date) & (data["fecha"] <= end_date)
    data = data[in_period]

    # Filtro por productos o categorías
    in_selected = data[element_column].isin(selected_elements)
    df = data[in_selected].copy()
    month = month_dict[ df["month"].iloc[0] ]
    year = df["year"].iloc[0]
    
    
    # Líneas interpoladas
    
    df["sales_day"]   = df.groupby([element_column, "fecha"])["cantidad"].transform("sum")
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
            ax.plot(plot_df["fecha"], plot_df["sales_day"], label= id+" (no hay datos)",
                marker="o", color=no_data_color)
            continue
        ax.plot(plot_df["fecha"], plot_df["sales_day"], label= id,
                marker="o", color=colors[i])
        
    # === Recta de tendencia === #
        # Convertir fechas a valores numéricos (ordinales)
        
        x = mdates.date2num(plot_df["fecha"])
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
        
    ax.set_title(f"Ventas diarias de {month},{year}", fontsize=16, fontweight="bold")
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
    fig.savefig("plots/almacen_ventas.png")
    return fig

def sales_velocity(data:pd.DataFrame,selected_elements:list,element_column: str,start_date,end_date):
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
    
    if data.empty:
        print("Dataset vacío")
        return None
    

    data["sales_velocity"] = data["sales_day"].rolling(window=2).mean()

    data["fecha"] = pd.to_datetime(data["fecha"], errors="coerce")

    
    start_date = pd.to_datetime(start_date)
    end_date   = pd.to_datetime(end_date)
    is_in_period = ( start_date <= data["fecha"] ) & ( data["fecha"] <= end_date )
    data = data[is_in_period]


    # Filtro por productos o categorías
    in_selected = data[element_column].isin(selected_elements)
    df = data[in_selected].copy()
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
            ax.plot(plot_df["fecha"], plot_df["sales_velocity"], label= id+" (no hay datos)",
                marker="o", color=no_data_color)
            continue
        ax.plot(plot_df["fecha"], plot_df["sales_velocity"], label= id,
                marker="o", color=colors[i])
        
    # === Recta de tendencia === #
        # Convertir fechas a valores numéricos (ordinales)
        
        x = mdates.date2num(plot_df["fecha"])
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
    fig.savefig("plots/almacen_v_rapidez_ventas.png")

    return fig

def sales_heat_map(data:pd.DataFrame,main_element:str,element_column:str,start_date,end_date):
    """ 
    Función que recibe el dataframe de datos del periodo especificado y 
    grafíca las ventas sobre un mapa de calor en méxico.
    """
    if data.empty:
        print("Dataset vacío")
        return None
    data["fecha"] = pd.to_datetime(data["fecha"], errors="coerce")
    start_date = pd.to_datetime(start_date)
    end_date   = pd.to_datetime(end_date)
    is_in_period = ( start_date <= data["fecha"] ) & ( data["fecha"] <= end_date )
    data = data[is_in_period]

    is_element=data[element_column]==main_element
    df_filtered=data[is_element]

    total_sales_per_state= df_filtered.groupby(["state"])["cantidad"].sum()
    mexico_estados = gpd.read_file("gadm41_MEX_shp/gadm41_MEX_1.shp")
    mexico_estados["state"] = mexico_estados["NAME_1"].str.upper()
    mexico_estados = mexico_estados.merge(total_sales_per_state, left_on="state",right_on="state")
    
    
    # --- Graficar heatmap --- #
    fig, ax = plt.subplots(1, 1, figsize=(12, 7))
    mexico_estados.plot(
        column="cantidad", 
        cmap="Blues",        # paleta más atractiva
        linewidth=0.5, 
        edgecolor="white",    # bordes blancos suaves
        legend=True, 
        legend_kwds={'shrink': 0.6, 'label': "Ventas"}, 
        ax=ax
    )

    # --- Estética --- #
    ax.set_title(f"Ventas de {main_element} por estado ", fontsize=16, fontweight='bold')
    ax.axis("off")
    fig.savefig("plots/heatmap_ventas_mexico.png")
    fig.patch.set_facecolor('lightgrey')  # fondo del mapa

    return fig
    
def sales_hist(data:pd.DataFrame,start_date,end_date):
    """
    Función que recibe el dataframe de datos del periodo especificado y 
    gráfica las curvas de existencia del producto y ventas.
    """
    if data.empty:
        print("Dataset vacío")
        return None
    data["fecha"] = pd.to_datetime(data["fecha"], errors="coerce")
    start_date = pd.to_datetime(start_date)
    end_date   = pd.to_datetime(end_date)
    is_in_period = ( start_date <= data["fecha"] ) & ( data["fecha"] <= end_date )
    data = data[is_in_period]

    

    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Bins alineados a enteros
    min_val = int(data["cantidad"].min())
    max_value = int(data["cantidad"].max())
    bins = range(min_val,max_value+10)
    
    counts, bin_edges, patches = ax.hist(data["cantidad"], 
            bins=bins, 
            color='blue', 
            edgecolor='black')
    
    # --- Etiquetas debajo de cada barra ---
    for i, patch in enumerate(patches):
        x_center = patch.get_x() + patch.get_width() / 2
        x_value  = int(bin_edges[i])  # valor del bin (entero)

        ax.text(
            x_center,                # centrado
            -0.5,                    # debajo del eje X
            str(x_value),            # etiqueta
            ha='center',
            va='top',
            fontsize=9
        )

    # Ocultar etiquetas del eje X
    ax.set_xticks([])

    ax.set_title("Frecuencia de Ventas", fontsize=14, fontweight='bold')
    ax.set_xlabel("Ventas diarias")
    ax.set_ylabel("Frecuencia")

    ax.yaxis.set_major_locator(MaxNLocator(integer=True))

    # Expandir ligeramente el espacio inferior para que quepan etiquetas
    plt.subplots_adjust(bottom=0.15)

    ax.grid(axis='y', linestyle='--', alpha=0.7)

    fig.tight_layout()
    fig.savefig("plots/hist_ventas_prod.png")
    return fig




def abc_bar_chart(data:pd.DataFrame,start_date:str,end_date:str,type:str="productos"):
    
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
        
    type_selected = type_dict[type]
    start_date = pd.to_datetime(start_date)
    end_date   = pd.to_datetime(end_date)

    data["fecha"] = pd.to_datetime(data["fecha"], errors="coerce")

    is_in_period = ( start_date <= data["fecha"] ) & ( data["fecha"] <= end_date )
    df_filtered = data[is_in_period]




    df_summary = (
        df_filtered
            .groupby(type_selected)
            .agg(
                total_sales=("cantidad", "sum"),
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
    fig.savefig(f"plots/{type}_abc_chart.png")

    return fig

