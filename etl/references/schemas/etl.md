# Inventario (etl.inventario)
| **Nombre de variable**                | **Descripción**                                                    | **Formato**                     | **Fuentes**                    |
| ------------------------------------- | ------------------------------------------------------------------ | ------------------------------- |------------------------------- |
| **inventory_id**(Primary Key)         | Llave identificadora de existencia de un producto dado en un día y almacen  |   Integer              | Auto generada                  |
| **product_id**(Foreign key)           | Llave identificadora de producto                                   |   VARCHAR                       | CT_Histórico/tbl_existenciasHistorial.productoReferencia.codigo  |
| **date**                              | Fecha asociada a la existencia                                     |   DATE                          | CT_Histórico/tbl_existenciasHistorial.fechaRegistro  |
| **stock**                             | Cantidad de unidades de producto disponibles en almacen            |   Integer                       | CT_Histórico/tbl_existenciasHistorial.almacenes  |
| **storage_id**(Foreign key)           | Llave identificadora de almacen                                    |   VARCHAR                       | CT_Histórico/tbl_existenciasHistorial.almacenes  |

# Ventas (etl.sales)

| **Nombre de variable**                | **Descripción**                                                             | **Formato**                     | **Fuentes**                    |
| ------------------------------------- | --------------------------------------------------------------------------- | ------------------------------- |------------------------------- |
| **sales_id**(Primary Key)             | Llave identificadora de venta de un producto dado en un día                 |   Integer                       | Auto generada                  |
| **product_id**(Foreign Key)           | Llave identificadora de productos,producto vendido                          |   VARCHAR                       | CT_API_Publica/Tabla de facturas.articulo   |
| **description**                       | Descripción del producto vendido                                            |   VARCHAR                       |  dashboard_app_db/raw.catalogo_productos    |
| **folio**                             | Folio de factura de venta                                                   |   VARCHAR                       | CT_API_Publica/Tabla de facturas.folio      |
| **quantity**                          | Cantidad de unidades vendidas                                               |   Integer                       | CT_API_Publica/Tabla de facturas.cantidad   |
| **date**                              | Fecha de venta                                                              |   DATE                          | CT_API_Publica/Tabla de facturas.fecha      |
| **total**                             | Total pagado en venta (MXN)                                                 |   REAL                          | CT_API_Publica/Tabla de facturas.total      |
| **price**                             | Precio de venta por unidad de producto (MXN)                                |   REAL                          | CT_API_Publica/Tabla de facturas.precio     |
| **cost**                              | Costo por unidad de producto (MXN)                                          |   REAL                          | dashboard_app_db/raw.catalogo_productos     |
| **client_id**(Foreign Key)            | Llave identificadora de clientes,cliente que realizó venta                  |   VARCHAR                       | CT_API_Publica/Tabla de facturas.cliente    |
| **sale_storage_id**(Foreign Key)      | Llave identificadora de almacenes,almacen del cual se extraeran las unidades de producto vendido  |  VARCHAR  | CT_API_Publica/Tabla de facturas.almacen    |

