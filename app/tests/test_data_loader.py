import pytest
import re
import pandas as pd
import datetime
from pathlib import Path
from pandas.testing import assert_frame_equal
from dashboard.data_loader import extract_table_parallel, update_table




# -----------------------------------------------
# BASE DE DATOS FALSA
# -----------------------------------------------
@pytest.fixture
def old_data():
    """
    Dataframe de dataset basal
    """
    return pd.DataFrame([{
        "id": f"PROD-{i}",
        "folio":f"FOLIO-{i}",
        "value": i * 10.0 ,
        "date": datetime.date(2025,12,1)} for i in range(20)
        
    ])

@pytest.fixture
def update_data():
    """
    Dataframe de datos nuevos que sirven para actualizar dataset basal
    """
    return pd.DataFrame([{
        "id": f"PROD-{i}",
        "folio":f"FOLIO-{i}",
        "value": i * 30.0 ,
        "date": datetime.date(2025,12,5)} for i in range(20,40) 
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

def fake_read_sql(query, conn)->pd.DataFrame:
    """
    Función que simula el comportamiento de extraer datos a partir de una consulta
    :param query: Consulta que se quiere realizar
    :param conn: Conexión a base de datos SQL Microsoft Server
    """
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

def fake_read_parquet_factory(old_data, update_data)->pd.DataFrame:
    """
    Simula la extracción de un dataset, dependiendo de que tipo se especifíque ya sea el viejo o el de actualización.
    :param old_data: Dataframe de pandas que sirve como proxy del dataset desactualizado.
    :param update_data: Dataframe de pandas que sirve como proxy de un dataset con información actualizada.
    """
    def fake_read_parquet(path, *args, **kwargs):
        path = str(path)
        if "update" in path:
            return update_data.copy()
        else:
            return old_data.copy()
    return fake_read_parquet

def make_fake_extract_table_parallel(update_data):
    """
    Parcheo de función de extracción en paralelo. Guarda el dataset de actualización en directorio especificado
    
    :param update_data: Dataframe de pandas que sirve como proxy de un dataset con información actualizada.
    """
    def fake_extract_table_parallel(query, output_file, *args, **kwargs):
        update_data.to_parquet(output_file)
    return fake_extract_table_parallel


# -----------------------------------------------------------
#  PRUEBAS
# -----------------------------------------------------------

@pytest.mark.parametrize("chunk_percent", [10, 25, 50, 100])
def test_no_data_loss(monkeypatch, tmp_path:Path, old_data,chunk_percent):
    """
    Prueba diseñada para verificar si los métodos de extracción de datos no pierden información al momento de ser ejecutados.

    
    :param monkeypatch: Herramienta para parcheo de funciones con fines de pruebas 
    :type monkeypatch: MonkeyPatch
    :param tmp_path: Ruta donde se guarda el dataset proxy
    :type tmp_path: Path
    :param old_data: Dataframe proxy de dataset viejo
    :type old_data: DataFrame
    :param chunk_percent: Porcentaje de dataset que los chunks usan para ajustar su tamaño al extraer información
    :type chunk_percent: Literal[10, 25, 50, 100]
    """
    fake_conn = FakeConn(old_data)
    monkeypatch.setattr("pyodbc.connect", lambda *args, **kwargs: fake_conn)
    monkeypatch.setattr("pandas.read_sql", fake_read_sql)

    output_file = tmp_path / "output.parquet"

    extract_table_parallel(
        query="SELECT * FROM test",
        output_file=output_file,
        connection_str="fake",
        order_column="id",
        chunk_percent=chunk_percent,
        temp_dir=tmp_path / "chunks"
    )

    result = pd.read_parquet(output_file)
    
    # Numero de filas
    assert len(result) == len(old_data),"El número de filas de la extracción debe ser estrictamente igual"
    # Numero de columnas
    assert list(result.columns) == list(old_data.columns),"Las columnas del dataset extraído debe ser igual al del origen"

    # Contenido,igualdad
    assert_frame_equal(result.reset_index(drop=True), old_data.reset_index(drop=True)),"El contenido del dataset extraído debe ser igual al del origen"





def test_update_table_partial(monkeypatch, tmp_path, old_data, update_data):
    """
    Prueba diseñada para verificar si los métodos de actualización de datos funcionan adecuadamente
    
    :param monkeypatch: Herramienta para parcheo de funciones con fines de pruebas 
    :type monkeypatch: MonkeyPatch
    :param tmp_path: Ruta de dataset proxy
    :type tmp_path: Path
    :param old_data: Dataframe proxy de dataset viejo
    :type old_data: DataFrame
    :param update_data: Dataframe proxy de dataset de actualización
    :type update_data: DataFrame
    """
    table_path = tmp_path / "data_table.parquet"
    old_data.to_parquet(table_path)

    fake_conn = FakeConn(update_data)
    
    monkeypatch.setattr("pyodbc.connect", lambda *a, **k: fake_conn)
    monkeypatch.setattr("pandas.read_sql", fake_read_sql)
    monkeypatch.setattr("ct_sales_dashboard.data_loader.extract_table_parallel", make_fake_extract_table_parallel(update_data))
    monkeypatch.setenv("TYPE_DICT", '{"id":"string","folio":"string","value":"float","date":"datetime64[ns]"}')
    monkeypatch.setenv("NAME_DICT",'{"id":"productId","value":"price"}')

    # Primera actualización
    update_table(
        table="data_table",
        latest_update=datetime.date(2025, 12, 1),
        save_dir=tmp_path
    )

    result = pd.read_parquet(table_path)
    expected = pd.concat([old_data, update_data], ignore_index=True).drop_duplicates()
   
    expected = expected.rename(columns={"id":"productId","value":"price"})
    expected = expected.astype({"productId":pd.StringDtype(storage="pyarrow"),
                                "folio":pd.StringDtype(storage="pyarrow"),
                                "price":"float",
                                "date":"datetime64[ns]"})

    assert_frame_equal(result.sort_values("folio").reset_index(drop=True),
                       expected.sort_values("folio").reset_index(drop=True),
                       check_dtype=False),"Resultado debe tener el mismo contenido que la concatenación de los datos viejos y actualizados"

def test_update_table_idempotent(monkeypatch, tmp_path, old_data, update_data):
    """
    Prueba diseñada para verificar que la actualización de tablas sea idempotente. Es decir, al aplicar el método n veces
    dara el mismo resultado que aplicar el método por una vez.
    
    :param monkeypatch: Herramienta para parcheo de funciones con fines de pruebas
    :type monkeypatch: MonkeyPatch
    :param tmp_path: Ruta de dataset proxy
    :type tmp_path: Path
    :param old_data: Dataframe proxy de dataset viejo
    :type old_data: DataFrame
    :param update_data: Dataframe proxy de dataset de actualización
    :type update_data: DataFrame
    """
    table_path = tmp_path / "data_table.parquet"
    old_data.to_parquet(table_path)

    fake_conn = FakeConn(update_data)
    monkeypatch.setattr("pyodbc.connect", lambda *a, **k: fake_conn)
    monkeypatch.setattr("pandas.read_sql", fake_read_sql)
    monkeypatch.setattr("dashboard.data_loader.extract_table_parallel", make_fake_extract_table_parallel(update_data))
    monkeypatch.setenv("TYPE_DICT", '{"id":"string","folio":"string","value":"float","date":"datetime64[ns]"}')
    monkeypatch.setenv("NAME_DICT", '{"id":"productId","value":"price"}')

    # 2 actualizaciones
    update_table(
        table="data_table",
        latest_update=datetime.date(2025, 12, 1),
        save_dir=tmp_path
    )
    update_table(
        table="data_table",
        latest_update=datetime.date(2025, 12, 1),
        save_dir=tmp_path
    )

    result = pd.read_parquet(table_path)
    expected = pd.concat([old_data, update_data], ignore_index=True).drop_duplicates()
    expected = expected.rename(columns={"id":"productId","value":"price"})
    expected = expected.astype({"productId":pd.StringDtype(storage="pyarrow"),
                                "folio":pd.StringDtype(storage="pyarrow"),
                                "price":"float",
                                "date":"datetime64[ns]"})

    # Asegurarse de duplicidad
    assert_frame_equal(result.sort_values("folio").reset_index(drop=True),
                       expected.sort_values("folio").reset_index(drop=True),
                       check_dtype=False),"Resultado debe tener el mismo contenido que la concatenación de los datos viejos y actualizados"
