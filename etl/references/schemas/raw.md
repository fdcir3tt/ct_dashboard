
# Clientes (raw.clientes)

| **Nombre de variable**                | **Descripción**                                                    | **Formato**                     | **Fuentes**                    |
| ------------------------------------- | ------------------------------------------------------------------ | ------------------------------- |------------------------------- |
| **clientId**(Key)                     | Llave identificadora de clientes                                   |   VARCHAR                       | DWH/Tabla de clientes          |
| **city**                              | Ciudad de donde originan los clientes                              |   VARCHAR                       | DWH/Tabla de clientes          |


# Productos (raw.productos)

| **Nombre de variable**                | **Descripción**                                                             | **Formato**                     | **Fuentes**                    |
| ------------------------------------- | --------------------------------------------------------------------------- | ------------------------------- |------------------------------- |
| **productId**(Primary Key)                    | Llave identificadora de productos                                           |   VARCHAR                       | DWH/Tabla de productos         |
| **categoryId**(Foreign Key)                    | Llave identificadora de categorías                                          |   VARCHAR                       | ctonline/ Tabla de productos        |
| **description**                       | Nombre y/o descripción de producto                                          |   TEXT                          | DWH/Tabla de productos         |
| **cost**                              | Costo del producto                                                          |   REAL                          | DWH/Tabla de productos         |
| **buy_coin**                          | Se refiere al tipo de moneda que se usa para comprar producto. 0:MXN, 1:USD |   Integer                       | DWH/Tabla de productos         |
| **sell_coin**                         | Se refiere al tipo de moneda que se usa para vender producto. 0:MXN, 1:USD  |   Integer                       | DWH/Tabla de productos         |


# Categorías (raw.categorias)

| **Nombre de variable**                | **Descripción**                                                    | **Formato**                     | **Fuentes**                    |
| ------------------------------------- | ------------------------------------------------------------------ | ------------------------------- |------------------------------- |
| **categoryId**(Primary Key)           | Llave identificadora de categoría                                  |   Integer                       | ctonline/ Tabla de categorías  |
| **parentId**(Foreign Key)             | Llave identificadora de categoría padre                            |   Integer                       | ctonline/ Tabla de productos   |
| **category**                          | Categoría en la que cae producto específicado                      |   VARCHAR                       | ctonline/ Tabla de categorías  |

# Almacenes (raw.almacenes)

| **Nombre de variable**                | **Descripción**                                                    | **Formato**                     | **Fuentes**                    |
| ------------------------------------- | ------------------------------------------------------------------ | ------------------------------- |------------------------------- |
| **storageId**(Key)                     | Llave identificadora de clientes                                   |   VARCHAR                       | DWH/Tabla de clientes          |
| **branch**                              | Ciudad de donde originan los clientes                              |   VARCHAR                       | DWH/Tabla de clientes          |
| **branchId**                              | Ciudad de donde originan los clientes                              |   VARCHAR                       | DWH/Tabla de clientes          |

# Geometrías (raw.geometrias)

| **Nombre de variable**                | **Descripción**                                                    | **Formato**                     | **Fuentes**                    |
| ------------------------------------- | ------------------------------------------------------------------ | ------------------------------- |------------------------------- |
| **state**(Primary Key)                | Nombre de estado Federal de México                                 |   VARCHAR                       |  Shapefile                     |
| **geometry**                          | Información geométrica de estado                                   |                                 |  Shapefile                     |
  

# Tazas históricas (raw.tazas_historicas)

| **Nombre de variable**                | **Descripción**                                                    | **Formato**                     | **Fuentes**                    |
| ------------------------------------- | ------------------------------------------------------------------ | ------------------------------- |------------------------------- |
| **date**(Primary Key)                 | Fecha de taza de conversión                                        |   DATE                          | Fecha  de extracción           |
| **exchange_rate**                     | Valor de taza de conversión de USD a MXN                           |   NUMERIC                       | Base histórica de tazas            |
  

# Tazas extraídas (raw.tazas_extraidas)

| **Nombre de variable**                | **Descripción**                                                    | **Formato**                     | **Fuentes**                    |
| ------------------------------------- | ------------------------------------------------------------------ | ------------------------------- |------------------------------- |
| **date**(Primary Key)                 | Fecha de taza de conversión                                        |   DATE                          | Fecha  de extracción           |
| **exchange_rate**                     | Valor de taza de conversión de USD a MXN                           |   NUMERIC                       | API de conversiones            |
| **fallback**                          | Método de imputación utilizada en el caso particular               |   VARCHAR                       | Método                         |


