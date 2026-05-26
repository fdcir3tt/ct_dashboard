# Ventas (marts.informacion_ventas)

| **Nombre de variable**                | **Descripción**                                                             | **Formato**                     | **Fuentes**                                              |
| ------------------------------------- | --------------------------------------------------------------------------- | ------------------------------- |----------------------------------------------------------|
| **sales_id**(Primary Key)             | Llave identificadora de venta de un producto dado en un día                 |  Integer                        | dashboard_app_db/etl.ventas         |
| **product_id**(Foreign Key)           | Llave identificadora de productos,producto vendido                          |   VARCHAR                       | dashboard_app_db/etl.ventas         |
| **category_id**(Foreign Key)          | Llave identificadora de categorías,categoría vendida                        |   VARCHAR                       | dashboard_app_db/etl.ventas         |
| **folio**                             | Folio de factura de venta                                                   |   VARCHAR                       | dashboard_app_db/etl.ventas         |
| **quantity**                          | Cantidad de unidades vendidas                                               |   Integer                       | dashboard_app_db/etl.ventas         |
| **date**                              | Fecha de venta                                                              |   DATE                          | dashboard_app_db/etl.ventas         |
| **price**                             | Precio de unidad de producto (MXN)                                          |   REAL                          | dashboard_app_db/etl.ventas         |
| **total**                             | Total pagado en venta (MXN)                                                 |   REAL                          | dashboard_app_db/etl.ventas         |
| **client_id**(Foreign Key)            | Llave identificadora de clientes,cliente que realizó venta                  |   VARCHAR                       | dashboard_app_db/etl.ventas         |
| **folio**                             | Folio de factura de venta                                                   |   VARCHAR                       | dashboard_app_db/etl.ventas         |
| **sale_storageId**(Foreign Key)       | Llave identificadora de almacenes,almacen del cual se extraeran las unidades de producto vendido  |  VARCHAR  | dashboard_app_db/etl.ventas         |
| **description**                       | Nombre y/o descripción de producto vendido                                  |   TEXT                          | dashboard_app_db/etl.ventas         |
| **cost**                              | Costo del producto  (MXN)                                                   |   REAL                          | dashboard_app_db/etl.ventas         |
| **branch_id**                         | Llave identificadora de sucursal,sucursal del cual se realizó la venta de producto                |   VARCHAR | dashboard_app_db/raw.catalogo_almacenes     |
| **branch**                            | Sucursal del cual se realizó la venta de producto                           |   VARCHAR                       | dashboard_app_db/raw.catalogo_almacenes     |
| **category**                          | Categoría vendida                                                           |   VARCHAR                       |  dashboard_app_db/raw.catalogo_categorias   |


# Inventario (marts.informacion_inventario)
| **Nombre de variable**                | **Descripción**                                                    | **Formato**                     | **Fuentes**                                                      |
| ------------------------------------- | ------------------------------------------------------------------ | ------------------------------- |------------------------------------------------------------------|
| **inventory_id**(Primary Key)         | Llave identificadora de existencia de un producto dado en un día y almacen  |   Integer              | dashboard_app_db/etl.inventario          |
| **productId**(Foreign key)            | Llave identificadora de producto                                   |   VARCHAR                       | dashboard_app_db/etl.inventario          |
| **date**                              | Fecha asociada a la existencia                                     |   DATE                          | dashboard_app_db/etl.inventario          |
| **stock**                             | Cantidad de unidades de producto disponibles en almacen            |   Integer                       | dashboard_app_db/etl.inventario          |
| **storage_id**(Foreign key)           | Llave identificadora de almacen                                    |   VARCHAR                       | dashboard_app_db/etl.inventario          |
| **branch**                            | Sucursal del cual corresponge el almacen venta de producto         |   VARCHAR                       | dashboard_app_db/raw.catalogo_almacenes  |
| **category**                          | Categoría de producto almacenado                                   |   VARCHAR                       | dashboard_app_db/raw.catalogo_categorias |