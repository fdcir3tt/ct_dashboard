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
    Agrega columna de estado Méxicano a la tabla ingresada

    Parametros:
    - data: pandas.DataFrame, Datos de ingreso con columna de sucursal

    Regresa:
    - df: pandas.DataFrame, Datos con columna de estados Méxicanos agregada.
    """

    df = data.copy()
    with open("states_dict.json", "r", encoding="utf-8") as f:
            states_dict = json.load(f)

    df["state"] = df["branch"].map(states_dict).fillna("UNKNOWN")
    return df

def top_n(data:pd.DataFrame,element_column:str,type:str="producto",criteria:str="ventas_diarias",n:int=5)->pd.DataFrame:
    """
    Recibe el dataframe de datos del periodo especificado y regresa los mejores
    'n' productos o categorías en base el criterio específicado.

    Parametros:
    - data: pandas.DataFrame, Datos de facturas de venta
    - element_column: str , Nombre de columna clasificadora de elementos. Es decir 'product_id' para productos o 'category' para categoría de producto
    - type: str, Tipo de elemento que se quiere extraer.
    - criteria: str , Criterio en base cual se compararán los elementos. Ya sea ventas diarias, mensuales etc.
    - n: int, Cantidad de elementos seleccionados de los mejores.
    Regresa:
    - top_n: pandas.DataFrame, Datos de los mejores 'n' elementos en base el criterio específicado.
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
    Genera una lista de fechas en el periodo designado

    Parametros:
    - start_date: Date , Fecha inicio del periodo
    - end_date: Date , Fecha fin del periodo
    Regresa:
    - dates:list[Date], Lista de fechas entre 'start_date' y 'end_date'

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

    if previous == 0:
        return 0
    return round(((current - previous) / previous) * 100, 2)

def calculate_iqr_bounds(sales_series:pd.Series)->tuple[float,float]:
    q1 = sales_series.quantile(0.25)
    q3 = sales_series.quantile(0.75)
    iqr = q3 - q1
    return (q1 - 1.5 * iqr, q3 + 1.5 * iqr)


def identify_outlier_sales(data: pd.DataFrame,
                           element_column:str)->pd.DataFrame:
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
                                       period_start:Date,
                                       period_end:Date)->tuple[str,str]:
    df = data.copy()
    is_in_period = ( period_start <= df['date'] ) & ( df['date'] <= period_end )
    
    if df[is_in_period].empty:
        top_product= (
            data
            .groupby("product_id")["quantity"]
            .sum()
            .idxmax()
        )
        top_category= (
        data
        .groupby("category")["quantity"]
        .sum()
        .idxmax()
    )   
        return top_product,top_category
    else:     
        top_product= (
            data[is_in_period]
            .groupby("product_id")["quantity"]
            .sum()
            .idxmax()
        )
        top_category= (
        data[is_in_period]
        .groupby("category")["quantity"]
        .sum()
        .idxmax()
    )   
        return top_product,top_category
    
def calculate_frequent_branch(data:pd.DataFrame,top_product:str)->str:
    is_top_product= data["product_id"]==top_product
    frequent_branch= (
        data[is_top_product]
        .groupby("branch")["date"]
        .nunique() 
        .idxmax()
    )
    return frequent_branch


