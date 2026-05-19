import pandas as pd

from common.registry import register
from common.db import upsert_df,create_table
from airflow.providers.postgres.hooks.postgres import PostgresHook

load_conditions = {"clean_rates_df"   :"stop" }
tag = "currency_rates"

@register(tag)
def load_clean_rates_df(conn_str:str,transformed_data:dict[str,pd.DataFrame]):
    clean_rates_df = transformed_data["clean_rates_df"]
    hook = PostgresHook(postgres_conn_id=conn_str)
    print("Creando tabla de conversiones USD->MXN de moneda limpias...")

    # Categorías
    create_table(hook,"staging","tazas_clean",{"date"           :"DATE PRIMARY KEY",
                                               "exchange_rate"  :"NUMERIC"})
                                    
    print("Poblando tabla de conversiones USD->MXN de moneda limpias...")
    upsert_df(hook,"staging","tazas_clean",clean_rates_df,["date"])

    

