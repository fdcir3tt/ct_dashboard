import streamlit as st
import pandas as pd
import yaml
import streamlit_authenticator as stauth
import streamlit.components.v1 as components
import datetime
import json
from yaml.loader import SafeLoader
from functools import wraps


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
    df = data.copy()
    with open("states_dict.json", "r", encoding="utf-8") as f:
            states_dict = json.load(f)

    df["state"] = df["branch"].map(states_dict).fillna("UNKNOWN")
    return df

def top_n(data:pd.DataFrame,
          element_column,
          type:str="producto",
          criteria:str="ventas_diarias",
          n:int=5)->list[str]:
    """
    Recibe el dataframe de datos del periodo especificado y regresa los mejores
    'n' productos o categorías en base el criterio específicado.
    """
    type_dict= {"producto":"productId",
                "categoria":"category",
                "branch":"branch",
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

def frequency(data:pd.DataFrame,
              type:str="cliente")->pd.DataFrame:
    """
    Recibe el dataframe de datos del periodo especificado y regresa los ritmos de ventas promedio
    en dicho periodo. 

    """
    if data.empty:
        print("Dataset vacío")
        return None
    type_dict= {"producto":"productId",
                "categoria":"category",
                "branch":"branch",
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

def frequent_clients(data:pd.DataFrame,
                     level:str="producto",
                     n:int=5)->list[str]:
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


def time_period(start_date: datetime.datetime,
                end_date: datetime.datetime = datetime.datetime.today()) -> list:
    if start_date > end_date:
        raise ValueError("Fecha inicial debe tomar lugar antes que la fecha final de periodo")

    dates = []
    current = start_date

    while current <= end_date:
        dates.append(current)
        current += datetime.timedelta(days=1)

    return dates


def load_css(file_name):

    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

