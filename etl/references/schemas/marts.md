# Ventas (marts.ventas)

| **Nombre de variable**                | **Descripción**                                                             | **Formato**                     | **Fuentes**                    |
| ------------------------------------- | --------------------------------------------------------------------------- | ------------------------------- |------------------------------- |
| **salesId**(Primary Key)              | Llave identificadora de venta de un producto dado en un día                 |   VARCHAR                       | Codificación de "folio-productId-date-clientId"       |
| **productId**(Foreign Key)            | Llave identificadora de productos,producto vendido                          |   VARCHAR                       | DWH/Tabla de productos         |
| **folio**                             | Folio de factura de venta                                                   |   VARCHAR                       | fuente        |
| **quantity**                          | Cantidad de unidades vendidas                                               |   Integer                       | fuente        |
| **date**                              | Fecha de venta                                                              |   DATE                          | fuente        |
| **total**                             | Total pagado en venta (MXN)                                                 |   REAL                          | fuente        |
| **clientId**(Foreign Key)             | Llave identificadora de clientes,cliente que realizó venta                  |   VARCHAR                       | fuente        |
| **sale_storageId**(Foreign Key)       | Llave identificadora de almacenes,almacen del cual se extraeran las unidades de producto vendido  |  VARCHAR  | fuente        |




