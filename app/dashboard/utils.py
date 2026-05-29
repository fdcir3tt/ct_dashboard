import json
import datetime
import pandas as pd




Date = datetime.datetime
Document =  dict[str, any]
Documents = list[Document]

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

def add_states_column(data:pd.DataFrame)->pd.DataFrame:
    """
    Agrega una columna de estado mexicano al DataFrame a partir de la sucursal.

    Lee un diccionario de mapeo sucursal → estado desde el archivo
    `states_dict.json` y lo aplica sobre la columna `branch`.

    Parameters
    ----------
    data : pd.DataFrame
        DataFrame de entrada con columna `branch` que contiene los nombres
        de las sucursales.

    Returns
    -------
    pd.DataFrame
        Copia del DataFrame original con la columna `state` agregada.
        Las sucursales sin mapeo correspondiente toman el valor `'UNKNOWN'`.
    """

    df = data.copy()
    with open("states_dict.json", "r", encoding="utf-8") as f:
            states_dict = json.load(f)

    df["state"] = df["branch"].map(states_dict).fillna("UNKNOWN")
    return df

def top_n(data:pd.DataFrame,element_column:str,type:str="producto",criteria:str="ventas_diarias",n:int=5)->pd.DataFrame:
    """
    Retorna los mejores o peores N elementos según un criterio de rendimiento.

    Calcula las ventas diarias por elemento y ordena según el criterio
    indicado. Soporta selección del mejor elemento único (`n=1`), los
    mejores N (`n>1`) y los peores N (`n<0`).

    Parameters
    ----------
    data : pd.DataFrame
        Datos de facturas de venta. Debe contener las columnas `date`,
        `quantity`, y la columna indicada en `element_column`.
    element_column : str
        Nombre de la columna clasificadora de elementos.
        Use `'product_id'` para productos o `'category'` para categorías.
    type : {'producto', 'categoria', 'branch', 'cliente'}, optional
        Tipo de elemento a extraer. Determina la columna de agrupación.
        Por defecto `'producto'`.
    criteria : {'ventas_diarias', 'ventas_mensuales', 'ganancia_total'}, optional
        Métrica de comparación entre elementos. Por defecto `'ventas_diarias'`.
    n : int, optional
        Cantidad de elementos a retornar. Si `n=1` retorna el mejor elemento
        como string. Si `n<0` retorna los `abs(n)` peores elementos.
        Por defecto 5.

    Returns
    -------
    pd.DataFrame
        DataFrame con los N mejores (o peores) elementos y su métrica,
        ordenados de forma descendente (o ascendente si `n<0`).
    str
        Identificador del mejor elemento cuando `n=1`.

    Notes
    -----
    La columna `sales_day` se calcula internamente como la suma de
    `quantity` agrupada por `element_column` y `date`, modificando
    el DataFrame de entrada en lugar de operar sobre una copia.
    """
    type_dict= {"producto":"product_id",
                "categoria":"category",
                "branch":"branch",
                "cliente":"client_id"}

    criteria_dict={"ventas_diarias":"sales_day",
                   "ventas_mensuales":"sales_month",
                   "ganancia_total":"total_profit"}
    
    data["sales_day"] = (data.groupby([element_column, "date"])["quantity"]
                             .transform("sum") )
    
    columns=[ type_dict[type], criteria_dict[criteria]]
    if n==1:
        top_n= (data[columns].sort_values(by=criteria_dict[criteria],ascending=False)[type_dict[type]]
                             .iloc[0])
        return top_n
    
    if n<0 :
        df= (data[columns].sort_values(by=criteria_dict[criteria],ascending=True)
                          .drop_duplicates()[:abs(n)])
        return df
    
    df= (data[columns].sort_values(by=criteria_dict[criteria],ascending=False)
                      .drop_duplicates()[:n])
    top_n= df

    return top_n


def time_period(start_date: Date, end_date: Date = Date.today()) -> list[Date]:
    """
    Genera una lista de fechas diarias dentro de un período dado.

    Parameters
    ----------
    start_date : Date
        Fecha de inicio del período (incluida).
    end_date : Date, optional
        Fecha de fin del período (incluida). Por defecto la fecha actual.

    Returns
    -------
    list of Date
        Lista de fechas desde `start_date` hasta `end_date`, inclusive,
        con incrementos de un día.

    Raises
    ------
    ValueError
        Si `start_date` es posterior a `end_date`.
    """
    if start_date > end_date:
        raise ValueError("Fecha inicial debe tomar lugar antes que la fecha final de periodo")

    dates = []
    current = start_date

    while current <= end_date:
        dates.append(current)
        current += datetime.timedelta(days=1)

    return dates


def growth_rate(current:float, previous:float):
    """
    Calcula la tasa de crecimiento porcentual entre dos valores.

    Parameters
    ----------
    current : float
        Valor del período actual.
    previous : float
        Valor del período anterior.

    Returns
    -------
    float
        Tasa de crecimiento expresada como porcentaje, redondeada a
        dos decimales. Retorna `0` si `previous` es igual a cero para
        evitar división por cero.

    Examples
    --------
    >>> growth_rate(120, 100)
    20.0
    >>> growth_rate(80, 100)
    -20.0
    >>> growth_rate(50, 0)
    0
    """
    if previous == 0:
        return 0
    return round(((current - previous) / previous) * 100, 2)

def calculate_iqr_bounds(sales_series:pd.Series)->tuple[float,float]:
    """
    Calcula los límites inferior y superior del rango intercuartílico (IQR).

    Usa la regla estándar de Tukey: límite inferior = Q1 - 1.5·IQR,
    límite superior = Q3 + 1.5·IQR.

    Parameters
    ----------
    sales_series : pd.Series
        Serie numérica de valores de ventas sobre la que se calculan
        los cuartiles.

    Returns
    -------
    tuple of float
        Par `(lower_bound, upper_bound)` donde los valores fuera de
        este rango se consideran atípicos.
    """
    q1 = sales_series.quantile(0.25)
    q3 = sales_series.quantile(0.75)
    iqr = q3 - q1
    return (q1 - 1.5 * iqr, q3 + 1.5 * iqr)


def identify_outlier_sales(data: pd.DataFrame,
                           element_column:str)->pd.DataFrame:
    """
    Identifica registros de ventas atípicas mediante el método IQR por elemento.

    Calcula los límites IQR de forma independiente para cada elemento
    agrupado por `element_column` y marca como outlier cualquier registro
    cuya `quantity` quede fuera de esos límites.

    Parameters
    ----------
    data : pd.DataFrame
        Datos de facturas de venta. Debe contener la columna `quantity`
        y la columna indicada en `element_column`.
    element_column : str
        Nombre de la columna clasificadora de elementos.
        Use `'product_id'` para productos o `'category'` para categorías.

    Returns
    -------
    pd.DataFrame
        Copia del DataFrame original con la columna booleana `is_outlier`
        agregada. El valor es `True` cuando la venta se considera atípica
        y `False` en caso contrario.
    """
    df = data.copy()

    bounds_dict = df.groupby(element_column)['quantity'].apply(calculate_iqr_bounds).to_dict()
    
    df['iqr_bounds'] = df[element_column].map(bounds_dict)
    df['is_outlier'] = ~df['quantity'].between(
                                              df['iqr_bounds'].str[0], 
                                              df['iqr_bounds'].str[1]
                                              )

    df = df.drop(columns='iqr_bounds')
    return df

def calculate_top_product_and_category(data:pd.DataFrame,
                                       branch:str,
                                       period_start:Date,
                                       period_end:Date)->tuple[str,str]:
    """
    Determina el producto y la categoría con mayor volumen de ventas
    en una sucursal y período dados.

    Si no existen registros dentro del período, utiliza todos los datos
    históricos de la sucursal como alternativa.

    Parameters
    ----------
    data : pd.DataFrame
        Datos de facturas de venta. Debe contener las columnas `date`,
        `branch`, `product_id`, `category` y `quantity`.
    branch : str
        Nombre de la sucursal a analizar.
    period_start : Date
        Fecha de inicio del período de análisis (incluida).
    period_end : Date
        Fecha de fin del período de análisis (incluida).

    Returns
    -------
    top_product : str
        Identificador del producto con mayor cantidad vendida en el período.
    top_category : str
        Nombre de la categoría con mayor cantidad vendida en el período.
    """
    df = data.copy()
    is_in_period = ( period_start <= df['date'] ) & ( df['date'] <= period_end )
    in_branch = df['branch'] == branch

    
    if df[is_in_period].empty:
        top_product= (
            data[in_branch]
            .groupby("product_id")["quantity"]
            .sum()
            .idxmax()
        )
        top_category= (
        data[in_branch]
        .groupby("category")["quantity"]
        .sum()
        .idxmax()
    )   
        return top_product,top_category
    else:     
        filtered_df = df[is_in_period & in_branch]
        top_product= (
            filtered_df
            .groupby("product_id")["quantity"]
            .sum()
            .idxmax()
        )
        top_category= (
        filtered_df
        .groupby("category")["quantity"]
        .sum()
        .idxmax()
    )   
        return top_product,top_category
    
def calculate_frequent_branch(data:pd.DataFrame,top_product:str)->str:
    """
    Determina la sucursal donde un producto ha sido vendido con mayor
    frecuencia en términos de días distintos con ventas.

    Parameters
    ----------
    data : pd.DataFrame
        Datos de facturas de venta. Debe contener las columnas `product_id`,
        `branch` y `date`.
    top_product : str
        Identificador del producto a analizar.

    Returns
    -------
    str
        Nombre de la sucursal con el mayor número de días distintos
        con ventas del producto indicado.
    """
    is_top_product= data["product_id"]==top_product
    frequent_branch= (
        data[is_top_product]
        .groupby("branch")["date"]
        .nunique() 
        .idxmax()
    )
    return frequent_branch


