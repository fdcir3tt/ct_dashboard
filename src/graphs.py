import pandas as pd
import geopandas as gpd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates



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
        top_n= list( data[ criteria_dict[criteria] ].max()[type_dict[type]] )
        return 
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
    type_dict= {"producto":"productId",
                "categoria":"category",
                "sucursal":"branch",
                "cliente":"client",
                "dia":"weekday"}
    
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
                  5:"Dábado",
                  6:"Domingo"}
    
    data["fecha"] = pd.to_datetime(data["fecha"])
    data["weekday"]=data["fecha"].dt.weekday
    df = frequency(data,type="dia")
    df = df.sort_values(by="avg_rate",ascending=False)
    return weekday_dict[df["weekday"].iloc[0]]

def stock_v_sales(data: pd.DataFrame,productId:str):
    """
    Grafica curvas de stock y ventas con estética mejorada,
    eje X limpio, datos interpolados y fechas correctamente manejadas.
    """
    is_product=data["productId"]==productId
    df_filtered=data[is_product]

    data = df_filtered.copy()

    # --- Asegurar que las fechas SON datetime ---
    data["fecha"] = pd.to_datetime(data["fecha"], errors="coerce")

    # Eliminar filas con fechas inválidas que causen el 1970-01-01
    data = data.dropna(subset=["fecha"]).sort_values("fecha")

    # --- Interpolación lineal ---
    data["sales_day"] = data["sales_day"].interpolate(method="linear")
    data["stock"]     = data["stock"].interpolate(method="linear")

    plt.figure(figsize=(12, 6))
    plt.style.use("seaborn-v0_8")

    # Líneas interpoladas
    plt.plot(data["fecha"], data["sales_day"], label="Ventas", marker="o", color="#e63946")
    plt.plot(data["fecha"], data["stock"],     label="Stock", marker="s", color="#457b9d")

    # Título y etiquetas
    plt.title("Stock y Ventas (Interpolado)", fontsize=16, fontweight="bold")
    plt.xlabel("Fecha")
    plt.ylabel("Cantidad")

    # --- Eje X limpio ---
    ax = plt.gca()
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.xticks(rotation=45, ha="right")

    # Sin grid
    plt.grid(False)

    plt.legend()
    plt.tight_layout()
    plt.savefig("plots/almacen_ventas.png")
    plt.close()


def sales_heat_map(data:pd.DataFrame,productId:str):
    """ 
    Función que recibe el dataframe de datos del periodo especificado y 
    grafíca las ventas sobre un mapa de calor en méxico.
    """
    is_product=data["productId"]==productId
    df_filtered=data[is_product]

    total_sales_per_state= df_filtered.groupby(["state"])["cantidad"].sum()
    mexico_estados = gpd.read_file("gadm41_MEX_shp/gadm41_MEX_1.shp")
    mexico_estados["state"] = mexico_estados["NAME_1"].str.upper()
    mexico_estados = mexico_estados.merge(total_sales_per_state, left_on="state",right_on="state")
    
    
    # --- Graficar heatmap --- #
    fig, ax = plt.subplots(1, 1, figsize=(12, 12))
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
    ax.set_title("Mapa de calor de ventas por estado ", fontsize=16, fontweight='bold')
    ax.axis("off")
    fig.patch.set_facecolor('lightgrey')  # fondo del mapa

    fig.savefig("plots/heatmap_ventas_mexico.png", dpi=300, bbox_inches="tight")
    
def sales_hist(data:pd.DataFrame):
    """
    Función que recibe el dataframe de datos del periodo especificado y 
    gráfica las curvas de existencia del producto y ventas.
    """
    plt.figure(figsize=(10,6))
    plt.hist(data, bins=15, color='blue', edgecolor='black')
    plt.title("Histograma de Cantidad de Ventas", fontsize=14, fontweight='bold')
    plt.xlabel("Cantidad de ventas")
    plt.ylabel("Frecuencia")
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig("plots/hist_ventas_prod.png")

def profits_sales_bar(data:pd.DataFrame,categories:list[str]):
    """
    Función que recibe el dataframe de datos del periodo especificado y las categorias 
    seleccionadas,gráfica las barras de ganancia y cantidad de ventas lado a lado. 

    """
    is_category=data["category"].isin(categories)
    df_filtered=data[is_category]

    total_sales= df_filtered.groupby("category")["cantidad"].sum()
    total_profit= df_filtered.groupby("category")["profit"].sum()
    x = np.arange(len(categories))
    width = 0.4  # ancho de las barras

    fig, ax1 = plt.subplots(figsize=(10,6))

    # Barras de ventas (eje izquierdo)
    sales_bars = ax1.bar(x - width/2, total_sales, width, color='blue', label='Ventas')
    
    ax1.set_ylabel('Ventas', color='blue', fontsize=12)
    ax1.tick_params(axis='y', labelcolor='blue')
    ax1.set_xticks(x)
    ax1.set_xticklabels(categories)
    ax1.grid(axis='y', linestyle='--', alpha=0.5)

    # Barras de ganancias (eje derecho)
    ax2 = ax1.twinx()
    profit_bars = ax2.bar(x + width/2, total_profit, width, color='red', label='Ganancia')
    ax2.set_ylabel('Ganancia', color='red', fontsize=12)
    ax2.tick_params(axis='y', labelcolor='red')

    # Añadir título
    fig.suptitle('Ventas y Ganancia por Categoría', fontsize=14, fontweight='bold')
    fig.tight_layout()
    plt.savefig("plots/bar_ventas_ganancia.png")

def sales_freq_bar(data:pd.DataFrame):
    """
    Función que recibe el dataframe de datos del periodo especificado y las categorias 
    seleccionadas,gráfica las barras de ganancia y cantidad de ventas lado a lado. 

    """
    products = top_n(data=data,type="producto")

    is_in_products= data["productId"].isin(products)
    frequencies = data[is_in_products].value_counts()
    
    plt.figure(figsize=(10,6))
    bars = plt.bar(products, frequencies, color="blue", edgecolor='black')

    # --- Etiquetas sobre cada barra ---
    for bar in bars:
        altura = bar.get_height()
        plt.text(
            bar.get_x() + bar.get_width()/2, 
            altura + 5,  # un poco arriba de la barra
            str(altura),
            ha='center', 
            va='bottom',
            fontsize=10,
            fontweight='bold'
        )

    # --- Estética ---
    plt.title('Frecuencia de compra de productos electrónicos en periodo', fontsize=16, fontweight='bold')
    plt.xlabel('Productos', fontsize=12)
    plt.ylabel('Cantidad de compras', fontsize=12)
    plt.grid(axis='y', linestyle='--', alpha=0.5)
    plt.tight_layout()
    plt.savefig("plots/bar_frecs_compras.png")


