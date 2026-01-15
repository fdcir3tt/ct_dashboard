from dotenv import load_dotenv
import os
import datetime
import pandas as pd
from src.graphs import *

load_dotenv()
data_columns = os.getenv("SALES_DATA_COLUMNS")


graphs = [period_sales,sales_velocity,sales_hist,interactive_sales_heat_map,abc_bar_chart]
mono_graphs =[period_sales,sales_velocity,sales_hist]
    
# -----------------------------------------------------------
# CARGA DE DATOS
# -----------------------------------------------------------

df = pd.read_parquet("data/processed.parquet")
df["income"] = df["price"] * df["quantity"]

def load_invoices():
    df = pd.read_parquet("data/facturas.parquet",engine="pyarrow",dtype_backend="pyarrow")
    
    return df

def load_products():
    categories = pd.read_parquet("data/categorias.parquet")
    products = pd.read_parquet("data/productos.parquet")

    products = products.merge(categories,how="left",on="idCategoria")
    products = products [["clave","nombre"]]
    products = products.rename(columns={"nombre":"category"})
    return products

def load_categories():
    categories = pd.read_parquet("data/categorias.parquet")
    categories = categories [["nombre"]]
    return categories

# -----------------------------------------------------------
# VALORES PREDETERMINADOS
# -----------------------------------------------------------

today = datetime.date.today()
start_date = datetime.date(today.year, today.month, 1)
end_date = today
start_date = pd.to_datetime(start_date)
end_date   = pd.to_datetime(end_date)


df["date"] = pd.to_datetime(df["date"], errors="coerce")


# Producto con más unidades vendidas
is_in_period = ( start_date <= df["date"] ) & ( df["date"] <= end_date )
top_product= (
    df[is_in_period]
    .groupby("productId")["quantity"]
    .sum()
    .idxmax()
)
product_list = list( df["productId"].unique() )
top_product_index = product_list.index(top_product)

# Sucursal en donde se vende más seguido el producto más vendido
is_top_product= df["productId"]==top_product
frequent_branch= (
    df[is_top_product]
    .groupby("sucursal")["date"]
    .nunique() 
    .idxmax()
)
branch_list = list( df[is_top_product]["sucursal"].unique() )
frequent_branch_index = branch_list.index(frequent_branch)

# Categoría con más unidades vendidas
top_category= (
    df[is_in_period]
    .groupby("category")["quantity"]
    .sum()
    .idxmax()
)
category_list = list( df["category"].unique() )
top_category_index = category_list.index(top_category)


fecha_inicio = start_date
fecha_fin = today
fecha_inicio = pd.to_datetime(fecha_inicio)
fecha_fin   = pd.to_datetime(fecha_fin)




is_category = df["category"]==top_category
is_category = df["productId"]==top_product
in_branch = df["sucursal"] == frequent_branch
is_in_period = ( fecha_inicio <= df["date"] ) & ( df["date"] <= fecha_fin )

df["sales_day"]   = df.groupby(["productId", "date"])["quantity"].transform("sum")
df["category_sales_day"]   = df.groupby(["category", "date"])["quantity"].transform("sum")
df["date"] = pd.to_datetime(df["date"])
df["month"] = df["date"].dt.month
df["year"] = df["date"].dt.year
df["income"] = df["price"] * df["quantity"]

# -----------------------------------------------------------
# PRUEBAS
# -----------------------------------------------------------


def test_total_sales_consistency():
    """
    Información desplegada por gráficos deben ser la misma. En este caso queremos que todas las gráficas
    coincidan en la cantidad total de ventas del elemento seleccionado. 
    """
    sales = set()
    total_branch_sales = set()
    is_product = df["productId"]==top_product
    is_in_period = ( fecha_inicio <= df["date"] ) & ( df["date"] <= fecha_fin )
    total_sales = df[is_product & is_in_period]["quantity"].sum()
    sales.add(total_sales)
    for g in graphs:
        _,dummy_df = g(data=df,
                   selected_elements=[top_product],
                   main_element=top_product,
                   element_column="productId",
                   branch=frequent_branch,
                   start_date=fecha_inicio,
                   end_date=fecha_fin,
                   type ="productos",
                   val=True)
        
        if g==abc_bar_chart:
            is_product = dummy_df["productId"]==top_product
            branch_sales = dummy_df[is_product]["total_sales"].iloc[0]
            total_branch_sales.add(branch_sales)
            continue
        if g==interactive_sales_heat_map:
            total_sales = dummy_df["quantity"].sum()
            sales.add(total_sales)
            continue

        in_branch = dummy_df["sucursal"]==frequent_branch
        
        branch_sales = dummy_df[in_branch]["quantity"].sum()
        total_branch_sales.add(branch_sales)

    assert len(sales)==1 ,"Todas las gráficas deben coincidir en la venta total del producto a nivel global"
    assert len(total_branch_sales)==1 ,"Todas las gráficas deben coincidir en la venta total del producto a nivel sucursal"
    

def test_same_element_shown():
    """
    Prueba que determina si el elemento que se selecciona es el mismo para cada gráfica.
    """

    elements_shown=set()
    for g in mono_graphs:
        _,dummy_df = g(data=df,
                    
                   main_element=top_product,
                   selected_elements=[top_product],
                   element_column="productId",
                   branch=frequent_branch,
                   start_date=fecha_inicio,
                   end_date=fecha_fin,
                   val=True)
        elements_in_graph =dummy_df["productId"].unique()
        elements_shown.update(elements_in_graph)

    assert len(elements_shown)==1 ,"Todas las gráficas deben coincidir en el producto que estan manejando"


def test_top_product():
    """
    Prueba que verifica si todas las gráficas coinciden en el producto más vendido
    """
    top_products = set()
    for g in graphs:
        _,dummy_df = g(data=df,
                   selected_elements=[top_product],
                   main_element=top_product,
                   element_column="productId",
                   branch=frequent_branch,
                   start_date=fecha_inicio,
                   end_date=fecha_fin,
                   type ="productos",
                   val=True)
        
        if g==abc_bar_chart:
            top_products.add(
                        dummy_df[["productId","annual_value"]]
                        .iloc[0]["productId"]
                        )
            continue
        top_products.add(
                        dummy_df
                        .groupby("productId")["quantity"]
                        .sum()
                        .idxmax()
                        )
    assert len(top_products)==1 ,"Todas las gráficas deben coincidir en el producto con más unidades vendidas"
    assert top_products[0]==top_product ,"Todas las gráficas deben coincidir en el producto con más unidades vendidas cálculado al principio"
          


def test_null():
    """
    Prueba para verificar si hay valores nulos o no dentro de los datasets
    """
    df = load_invoices()
    assert not ( df.isna().any().any() ) ,"No deben existir campos vacíos en el dataset de facturas de venta"

def test_formats():
    """
    Prueba que verifica si las columnas de los datasets cumplen con los formatos establecidos
    """
    df = load_invoices()
    reference_input = {"productId":["ACC1243"],
                        "quantity":[5],
                        "date":["2025-01-02"],
                        "price":[3432.31],
                        "clientId":["CL301X"],
                        "folio":["HMO2993"],}
        
    reference_dtypes={"productId":"large_string[pyarrow]",
                        "quantity":"int32[pyarrow]",
                        "date":"timestamp[ns][pyarrow]",
                        "price":"float[pyarrow]",
                        "clientId":"large_string[pyarrow]",
                        "folio":"large_string[pyarrow]"}
        
    reference_df = pd.DataFrame(reference_input)
    reference_df["date"] = pd.to_datetime(reference_df["date"])
    reference_df = reference_df.astype(reference_dtypes)

    same_data_types = df.dtypes.equals(reference_df.dtypes)
    assert df.dtypes.equals(reference_df.dtypes),"Las columnas del dataset deben corresponder a las especifícadas en el diccionario de datos"


def test_value_ranges():
    """
    Prueba que determina si se cumple lógica básica en los datos. Ej: El precio y costo de cada producto debe ser positivo. Y el precio debe ser mayor al costo. 
    """
    invoices = load_invoices()
    products = load_products()
    merged_df = invoices.merge(products,how = "left",left_on="productId",right_on="clave")
    
    
    total_sales_category = merged_df.groupby("category")["quantity"].sum()
    total_sales_product = merged_df.groupby("productId")["quantity"].sum()
    same_sales_total = total_sales_product.sum() == total_sales_category.sum()

    positive_ranges = ( df["price"] > 0 )&( df["cost"] > 0 )&( df["quantity"] > 0 )
    assert positive_ranges.all(),"Los precios,costos y cantidades deben ser valores positivos"

    market_consistency = df["price"] > df ["cost"]
    assert market_consistency.all(),"El precio por unidad debe ser mayor al costo"
    
    valid_period = ( df["date"] >=pd.to_datetime( datetime.date(2020, 1, 1)) ) & ( df["date"] <= end_date )
    assert valid_period.all(),"Fechas deben caer dentro del periodo 2020 hasta la actualidad"
    

    df["sales_day"] = df.groupby("productId")["quantity"].transform("sum")
    df["sales_speed"] = df["sales_speed"] = (
    df.groupby("productId")["quantity"]
      .rolling(window=3, min_periods=1)
      .mean()
      .reset_index(level=0, drop=True)
)/3

    valid_speed = df["sales_day"] >= df["sales_speed"]
    assert valid_speed.all(),"Rápidez de venta diaria debe ser menor o igual a la venta diaria de cada producto"
    
    primary_key=["productId","clientId","folio"]
    unicity = len(df) == len(df[primary_key].drop_duplicates())
    assert len(df) == len(df[primary_key].drop_duplicates()),"La cantidad de de facturas por cliente y producto debe ser igual a la cantidad total de filas"


    assert  total_sales_product.sum() == total_sales_category.sum(),"Sumas de ventas por producto debe ser igual a la suma total por categoría"
    

