import pytest
import re
import pandas as pd
import datetime
from pandas.testing import assert_frame_equal
from data_loader import extract_table_parallel, update_table




# -----------------------------------------------
# BASE DE DATOS FALSA
# -----------------------------------------------
@pytest.fixture
def old_data():
    return pd.DataFrame([{
        "productId": f"PROD-{i}",
        "value": i * 10 } for i in range(20) 
    ])

@pytest.fixture
def update_data():
    return pd.DataFrame([{
        "productId": f"PROD-{i}",
        "value": i * 30 } for i in range(20,40) 
    ])
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
# -----------------------------------------------
#  AYUDA
# -----------------------------------------------

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

def fake_read_parquet_factory(old_data, update_data):
    """Returns a fake read_parquet function with closures"""
    def fake_read_parquet(path):
        path = str(path)
        if "update" in path:
            return update_data
        return old_data
    return fake_read_parquet


# -----------------------------------------------------------
#  PRUEBAS
# -----------------------------------------------------------

@pytest.mark.parametrize("chunk_percent", [10, 25, 50, 100])
def test_no_data_loss(monkeypatch, tmp_path, old_data,chunk_percent):
    fake_conn = FakeConn(old_data)
    monkeypatch.setattr("pyodbc.connect", lambda *args, **kwargs: fake_conn)
    monkeypatch.setattr("pandas.read_sql", fake_read_sql)

    output_file = tmp_path / "output.parquet"

    extract_table_parallel(
        query="SELECT * FROM test",
        output_file=str(output_file),
        connection_str="fake",
        file_format="parquet",
        order_column="id",
        chunk_percent=chunk_percent,
        temp_dir=str(tmp_path / "chunks")
    )

    result = pd.read_parquet(output_file)
    
    # Numero de filas
    assert len(result) == len(old_data)
    # Numero de columnas
    assert list(result.columns) == list(old_data.columns)

    # Contenido,igualdad
    assert_frame_equal(result.reset_index(drop=True), old_data.reset_index(drop=True))




def test_update_table_partial(monkeypatch, tmp_path, old_data, update_data):
    table_path = tmp_path / "data_table.parquet"
    old_data.to_parquet(table_path)

    fake_conn = FakeConn(update_data)
    
    monkeypatch.setattr("pyodbc.connect", lambda *a, **k: fake_conn)
    monkeypatch.setattr("pandas.read_sql", fake_read_sql)
    monkeypatch.setattr("data_loader.pd.read_parquet", 
                        fake_read_parquet_factory(old_data, update_data))

    # Primera actualización
    update_table(
        table="data_table",
        latest_update=datetime.date(2024, 1, 2),
        save_dir=str(tmp_path)
    )

    result = pd.read_parquet(table_path)
    expected = pd.concat([old_data, update_data], ignore_index=True).drop_duplicates()
    assert_frame_equal(result.sort_values("productId").reset_index(drop=True),
                       expected.sort_values("productId").reset_index(drop=True))

def test_update_table_idempotent(monkeypatch, tmp_path, old_data, update_data):
    table_path = tmp_path / "data_table.parquet"
    old_data.to_parquet(table_path)

    fake_conn = FakeConn(update_data)
    monkeypatch.setattr("pyodbc.connect", lambda *a, **k: fake_conn)
    monkeypatch.setattr("pandas.read_sql", fake_read_sql)
    monkeypatch.setattr("data_loader.pd.read_parquet", 
                        fake_read_parquet_factory(old_data, update_data))

    # 2 actualizaciones
    update_table(
        table="data_table",
        latest_update=datetime.date(2024, 1, 2),
        save_dir=str(tmp_path)
    )
    update_table(
        table="data_table",
        latest_update=datetime.date(2024, 1, 2),
        save_dir=str(tmp_path)
    )

    result = pd.read_parquet(table_path)
    expected = pd.concat([old_data, update_data], ignore_index=True).drop_duplicates()

    # Asegurarse de duplicidad
    assert_frame_equal(result.sort_values("productId").reset_index(drop=True),
                       expected.sort_values("productId").reset_index(drop=True))