from dotenv import load_dotenv
import os
import datetime
import pandas as pd


load_dotenv()
data_columns = os.getenv("SALES_DATA_COLUMNS")
data_path = "data/"

today = datetime.date.today()
start_date = datetime.date(today.year, today.month, 1)
end_date = today
start_date = pd.to_datetime(start_date)
end_date   = pd.to_datetime(end_date)


def load_invoices():
    df = pd.read_parquet(data_path+"facturas.parquet")
    df = df[data_columns.split(",")]
    rename_column_dict = {}
    rename_names = ["productId","folio","quantity","date","price","clientId"]
    i=0
    for col in data_columns.split(","):
        rename_column_dict[col]= rename_names[i]
        i+=1
    df = df.rename(columns=rename_column_dict)
    df = df.set_index(keys = "date" )
    return df

def load_products():
    categories = pd.read_parquet(data_path+"categorias.parquet")
    products = pd.read_parquet(data_path+"productos.parquet")

    products = products.merge(categories,how="left",on="idCategoria")
    products = products [["clave","nombre"]]
    products = products.rename(columns={"nombre":"category"})
    return products

def load_categories():
    categories = pd.read_parquet(data_path+"categorias.parquet")
    categories = categories [["nombre"]]
    return categories

def test_null():
    df = load_invoices()
    assert not ( df.isna().any().any() ) ,"No deben existir campos vacíos en el dataset de facturas de venta"

def test_formats():
    df = load_invoices()
    reference_input = {"productId":["ACC1243"],
                       "folio":["HMO2993"],
                       "quantity":[5],
                       "date":["2025-01-02"],
                       "price":[3432.31],
                       "clientId":["CL301X"]}
    
    reference_dtypes={"productId":"str",
                       "folio":"str",
                       "quantity":"int32",
                       "date":"datetime64[ns]",
                       "price":"float16",
                       "clientId":"str"}
    
    reference_df = pd.DataFrame(reference_input)
    reference_df["date"] = pd.to_datetime(reference_df["date"])
    reference_df = reference_df.astype(reference_dtypes)

    same_data_types = df.dtypes.equals(reference_df.dtypes)
    assert same_data_types,"Las columnas del dataset deben corresponder a las especifícadas en el diccionario de datos"


def test_value_ranges():
    df = load_invoices()
    products = load_products()
    merged_df = df.merge(products,how = "left",left_on="productId",right_on="clave")
    
    
    total_sales_category = merged_df.groupby("category")["quantity"].sum()
    total_sales_product = merged_df.groupby("productId")["quantity"].sum()
    same_sales_total = total_sales_product.sum() == total_sales_category.sum()
    assert same_sales_total,"Sumas de ventas por producto debe ser igual a la suma total por categoría"
    
    positive_ranges = ( df["price"] > 0 )&( df["cost"] > 0 )&( df["quantity"] > 0 )
    assert positive_ranges.all(),"Los precios,costos y cantidades deben ser valores positivos"

    market_consistency = df["price"] > df ["cost"]
    assert market_consistency.all(),"El precio por unidad debe ser mayor al costo"
    
    valid_period = ( df["date"] >= start_date )& ( df["date"] <= end_date )
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
    
    unicity = len(df) == len(df["folio"].unique())
    assert unicity,"La cantidad de folios de factura debe ser igual a la cantidad total de filas"


