# Ventas (marts.informacion_ventas)

| **Nombre de variable**                | **Descripción**                                                             | **Formato**                     | **Fuentes**                                              |
| ------------------------------------- | --------------------------------------------------------------------------- | ------------------------------- |----------------------------------------------------------|
| **salesId**(Primary Key)              | Llave identificadora de venta de un producto dado en un día                 |   VARCHAR                       | Codificación de "folio-productId-date-clientId"          |
| **productId**(Foreign Key)            | Llave identificadora de productos,producto vendido                          |   VARCHAR                       | DWH/Tabla de productos                                   |
| **categoryId**(Foreign Key)           | Llave identificadora de categorías,categoría vendida                        |   VARCHAR                       | ctonline/ Tabla de productos                             |
| **folio**                             | Folio de factura de venta                                                   |   VARCHAR                       | fuente        |
| **quantity**                          | Cantidad de unidades vendidas                                               |   Integer                       | fuente        |
| **date**                              | Fecha de venta                                                              |   DATE                          | fuente        |
| **price**                             | Precio de unidad de producto (MXN)                                          |   REAL                          | fuente        |
| **total**                             | Total pagado en venta (MXN)                                                 |   REAL                          | fuente        |
| **clientId**(Foreign Key)             | Llave identificadora de clientes,cliente que realizó venta                  |   VARCHAR                       | fuente        |
| **folio**                             | Folio de factura de venta                                                   |   VARCHAR                       | fuente        |
| **sale_storageId**(Foreign Key)       | Llave identificadora de almacenes,almacen del cual se extraeran las unidades de producto vendido  |  VARCHAR  | fuente        |
| **description**                       | Nombre y/o descripción de producto vendido                                  |   TEXT                          | DWH/Tabla de productos         |
| **sale_description**                  | Nombre y/o descripción de producto vendido                                  |   TEXT                          | fuente        |
| **cost**                              | Costo del producto  (MXN)                                                   |   REAL                          | DWH/Tabla de productos         |
| **storageId**(Foreign Key)            | Llave identificadora de almacenes,almacen del cual se extraeran las unidades de producto vendido  |   VARCHAR | fuente        |
| **branchId**                          | Llave identificadora de sucursal,sucursal del cual se realizó la venta de producto                |   VARCHAR | fuente        |
| **branch**                            | Sucursal del cual se realizó la venta de producto                           |   VARCHAR                       | fuente        |
| **category**                          | Categoría vendida                                                           |   VARCHAR                       |   fuente      |


# Inventario (marts.informacion_inventario)
| **Nombre de variable**                | **Descripción**                                                    | **Formato**                     | **Fuentes**                                                      |
| ------------------------------------- | ------------------------------------------------------------------ | ------------------------------- |------------------------------------------------------------------|
| **existenceId**(Primary Key)          | Llave identificadora de existencia de un producto dado en un día y almacen  |   VARCHAR              | Codificación de "productId-storageId-date"                       |
| **productId**(Foreign key)            | Llave identificadora de producto                                   |   VARCHAR                       | CT_Histórico/tbl_existenciasHistorial.productoReferencia.codigo  |
| **date**                              | Fecha asociada a la existencia                                     |   DATE                          | CT_Histórico/tbl_existenciasHistorial.fechaRegistro              |
| **stock**                             | Cantidad de unidades de producto disponibles en almacen            |   Integer                       | CT_Histórico/tbl_existenciasHistorial.almacenes                  |
| **storageId**(Foreign key)            | Llave identificadora de almacen                                    |   VARCHAR                       | CT_Histórico/tbl_existenciasHistorial.almacenes                  |
| **branch**                            | Sucursal del cual corresponge el almacen venta de producto         |   VARCHAR                       |                   |
| **category**                          | Categoría de producto almacenado                                   |   VARCHAR                       |                   |