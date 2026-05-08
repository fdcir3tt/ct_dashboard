# Tablas utilizadas

| **Nombre**                            | **Descripción**                                                    | **Proceso/Aplicación**          | **Dependencias**
| ------------------------------------- | ------------------------------------------------------------------ | ------------------------------- |------------------------------- | 
| **facturas**(facturas.parquet)        | Tabla de facturas    | (DWH Extracción de facturas )/dashboard          | data_loader.py|
| **categorias**(facturas.parquet)      | Tabla de categorías de producto   | ( Extracción de categorias)/dashboard          | data_loader.py|
| **productos**(productos.parquet)      | Tabla de facturas    | (DWH Extracción de productos -> Extracción de claves de categoría -> Merge )/dashboard          | data_loader.py|
| **ventas**(facturas_ventas.parquet)   | Tabla de ventas de producto     | (DWH Carga de facturas -> Carga de categorias->Merge con datos de moneda -> Filtros de producto)/dashboard          | data_loader.py,preprocess.py|
| **mapa_mexico**(gadm41_MEX_shp)       | Tabla de datos geográficos de la republica mexicana     | (Descarga de shapefile -> Descompresión de archivo)/dashboard          | shapefile_extraction.py,|
| **taza_de_moneda(MXN->USD)**(usd_mxn_rates.parquet) | Tabla de tazas extraídas de conversión de moneda MXN a USD     | (API de tazas -> actualización de tabla)/dashboard          | exchange_rates_update.py|
| **conversiones_de_moneda(USD a MXN)**(conversion_usd_mxn.parquet)| Tabla de tazas extraídas de conversión de moneda MXN a USD     | (Extraer datos de tazas -> Actualización de tabla)/dashboard          | exchange_rates_update.py,preprocess.py|
| **inventario**(base de datos)         | Tabla de historial de inventario de producto    | (Extraer información de historial de inventario-> Extraer información de sucursales->Extraer información de almacenes -> Mezclar información)/dashboard          | ingest.py |
| **sucursales**(base de datos)         | Tabla de sucursales y almacenes   |  (Extraer información de sucursales->Extraer información de almacenes -> Mezclar información)/dashboard          | data_loader.py|
| **dataset producto**(\<branchId\>_\<productId\>)| Tabla de ventas de un solo producto en una sola sucursal   |  (Extraer información de ventas->Filtrar por producto y sucursal)/mlops          | etl.py |
| **perfiles_datasets**(dataset_profiles.parquet) | Tabla de perfilado de datasets de producto  |  (Cargar dataset -> Validar -> Actualizar tabla)/mlops          | data_profiling.py |
| **clientes**(clients.parquet)         | Tabla de clientes de CT |  (Extracción de tabla de clientes )/mlops          | utils.py |


# Pipelines

| **Nombre**                            | **Descripción**                                                    | **Resultado**                   | **Fuentes**                    |
| ------------------------------------- | ------------------------------------------------------------------ | ------------------------------- |------------------------------- |
| **sales**                             | Extrae y procesa datos de factura a datos de ventas de producto    |    ventas                       | DWH/Tabla de facturas          |
| **categorical_info**                  | Extrae y procesa datos de producto y clientes                      |   categorías,productos,clientes | DWH/Tabla de productos,ctonline/ Tabla de categorías|
| **currency_rates**                    | Extrae y procesa datos de conversión de monedas                    | conversiones_de_moneda (USD a MXN) | API de tazas + archivo .csv |
| **inventory**                         | Extrae y procesa datos de historial de inventario y sucursales     |    inventario,sucursales        | CT_Historico/Tabla de historial,API_Publica/ Tabla de sucursales|
| **data_profiling**                    |  Aplica perfilado de datos de venta de producto                    |    perfiles_datasets            | ventas                         |