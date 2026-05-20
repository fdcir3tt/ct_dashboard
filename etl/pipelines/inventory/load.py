import pandas as pd

from common.registry import register
from common.db import upsert_df,create_table
from airflow.providers.postgres.hooks.postgres import PostgresHook


load_conditions = {"inventory_df"   :"stop" }
tag="inventory"

@register(tag)
def load_inventory_df(conn_str:str,transformed_data:dict[str,pd.DataFrame]):
    inventory_df = transformed_data["inventory_df"]
    hook = PostgresHook(postgres_conn_id=conn_str)
    print("Creando tabla de inventario...")

    # Categorías
    create_table(hook,"etl","inventario",{"inventory_id" :"INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY",
                                          "product_id"   :"VARCHAR",
                                          "date"         :"DATE",
                                          "stock"        :"BIGINT",
                                          "storage_id"   :"VARCHAR"},foreign_keys={
                                                                                  "storage_id":'raw.catalogo_almacenes(storage_id)'})
    print("Poblando tabla de inventario...")
    upsert_df(hook,"etl","inventario",inventory_df,["inventory_id"])

    
