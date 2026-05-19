import pandas as pd

from common.registry import register
from common.db import upsert_df,create_table
from airflow.providers.postgres.hooks.postgres import PostgresHook

load_conditions = {"sales_invoices_df"   :"stop" }
tag="sales"
@register(tag)
def load_sales_invoices_df(conn_str:str,transformed_data:dict[str,pd.DataFrame]):
    sales_invoices_df = transformed_data["sales_invoices_df"]
    hook = PostgresHook(postgres_conn_id=conn_str)
    print("Creando tabla de ventas...")
    create_table(hook,"etl","ventas",{  "sales_id"         :"INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY",
                                        'product_id'       :"VARCHAR",
                                        'description'      :"TEXT",
                                        'quantity'         :"Integer",
                                        'date'             :"DATE",
                                        'total'            :"REAL",
                                        'price'            :"REAL",
                                        'cost'             :"REAL",
                                        'client_id'        :"VARCHAR",
                                        'folio'            :"VARCHAR",
                                        'sale_storage_id'  :"VARCHAR",},foreign_keys={"sale_storage_id":"raw.catalogo_almacenes(storage_id)",
                                                                                      "product_id":"raw.catalogo_productos(product_id)"})
    print("Poblando tabla de ventas...")
    upsert_df(hook,"etl","ventas",sales_invoices_df,["sales_id"])

