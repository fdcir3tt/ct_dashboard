import pytest
import pandas as pd
import os
import shutil
import re
import datetime
from dotenv import load_dotenv
from  data_loader import extract_table_parallel, update_table

load_dotenv()
date_col=os.getenv("SALES_DATE_COLUMN")
data_columns=os.getenv("SALES_DATA_COLUMNS")
sales_art_col=os.getenv("SALES_ARTICLE_COLUMN")
price_col=os.getenv("SALES_PRICE")


# -----------------------------------------------
# BASE DE DATOS FALSA
# -----------------------------------------------

old_data = pd.DataFrame({
        date_col: [datetime.date(2024, 1, 1), datetime.date(2024, 1, 2)],
        "value": [10, 20]
    })

update_data = pd.DataFrame({
        date_col: [datetime.date(2024, 1, 3), datetime.date(2024, 1, 4)],
        "value": [30, 40]
    })

class FakeConn:
    def __init__(self, data):
        self.data = data

    def cursor(self):
        return self

    def execute(self, *args, **kwargs):
        return self

    def fetchall(self):
        return self.data

    def close(self):
        pass

def fake_read_sql(query, conn):
    df = conn.data

    if "COUNT(*)" in query:
        return pd.DataFrame({"NROWS": [len(df)]})

    
    
    offset_match = re.search(r"OFFSET\s+(\d+)\s+ROWS", query)
    fetch_match = re.search(r"FETCH NEXT\s+(\d+)\s+ROWS", query)

    if offset_match and fetch_match:
        offset = int(offset_match.group(1))
        size = int(fetch_match.group(1))
        return df.iloc[offset:offset+size].copy()

    return df.copy()

def fake_read_parquet(p):
        p = str(p)
        if "update" in p:
            return update_data
        else:
            return old_data

# -----------------------------------------------------------
#  PRUEBA DE PERDIDA DE FILAS
# -----------------------------------------------------------

def test_extract_table_parallel_no_data_loss(monkeypatch, tmp_path):

    # Dataset Falso
    df = pd.DataFrame({
        "id": range(20),
        "value": [x * 10 for x in range(20)]
    })

    
    fake_conn = FakeConn(df)
    

    # Monkeypatch simulando atributos de DB
    monkeypatch.setattr("pyodbc.connect", lambda *args, **kwargs: fake_conn)
    monkeypatch.setattr("pandas.read_sql", fake_read_sql)

    output_file = tmp_path / "output.csv"

    extract_table_parallel(
        query="SELECT * FROM test",
        output_file=str(output_file),
        connection_str="fake",
        file_format="csv",
        order_column="id",
        chunk_percent=25,  # 4 chunks
        temp_dir=str(tmp_path / "chunks")
    )

    result = pd.read_csv(output_file)
    assert len(result) == len(df)
    assert result.equals(df.reset_index(drop=True))


# -----------------------------------------------------------
#  PRUEBA DE CONCATENACIÓN
# -----------------------------------------------------------

def test_update_table(monkeypatch, tmp_path):

    table_path = tmp_path / "data_table.parquet"
    old_data.to_parquet(table_path)
    fake_conn = FakeConn(update_data)
    
    monkeypatch.setattr("pyodbc.connect", lambda *a, **k: fake_conn)
    monkeypatch.setattr("pandas.read_sql", fake_read_sql)
    monkeypatch.setattr("data_loader.pd.read_parquet", fake_read_parquet)

    
    update_table(
        table="data_table",
        latest_update= datetime.date(2024, 1, 2),
        save_dir=str(tmp_path)
    )

   
    result = pd.read_parquet(table_path)
    expected = pd.concat([old_data, update_data],ignore_index=True).drop_duplicates()

    assert result.equals(expected)
