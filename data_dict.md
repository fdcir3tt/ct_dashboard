# Diccionario de Datos


## Datos Crudos

| **Nombre**                            | **Descripción**                                                    | **Variable**         | **Formato de variable** | **Fuente**                  |
| ------------------------------------- | ------------------------------------------------------------------ | -------------------- | ----------------------- | --------------------------- |
| **código**                            | Código identificador de producto                                       | `ART_COD1`          | Texto / String          | Catálogo de artículos / DWH  |
| **código sustituto**                  | Código del producto que reemplazará al actual                      | `ART_COD2`    | Texto / String          | Catálogo de artículos / DWH |
| **categoría**                         | Categoría a la que pertenece el producto                           | `categorias.nombre`           | Texto / String          | Categorías / ctonline2 |
| **cliente**                  | Cliente del artículo indicado en factura de venta                | `VREN_CLI`    | Numérico / Decimal          | Catálogo de facturasdetalle / DWH |
| **cantidad pedida**                  | Cantidad de producto pedido en la factura de venta                      | `VREN_CANTIDAD`    | Numérico / Entero          | Catálogo de facturasdetalle / DWH |
| **fecha**                  | Fecha de venta indicada en factura de venta                      | `VREN_FCH`    | Fecha (YYYY-MM-DD)         | Catálogo de facturasdetalle / DWH |
| **precio de producto**                  | Precio por pieza al que se vendió artículo                 | `VREN_PRE`    | Numérico / Decimal          | Catálogo de facturasdetalle / DWH |
| **costo de producto**                  | Costo por pieza de artículo                 | `ART_COS`    | Numérico / Decimal          | Catálogo de artículos / DWH |
| **existencia de producto global**                  | Cantidad total de producto en almacen                 | `ART_COS`    | Numérico / Entero          | Tabla de existencia / CT_API_Publica |
| **existencia de producto_{homoclave}**                  | Cantidad de producto en almacen con homoclave indicada                | `almacenes.existencia`    | Numérico / Entero          | Tabla de existencia / CT_API_Publica |
| **ubicación sucursal**                  | Ubicación geográfica en donde se situa sucursal                | `sucursal`    | Texto / String          | Tabla de almacenes / CT_API_Publica |

## Datos Procesados

| **Nombre**                            | **Descripción**                                                    | **Variable**         | **Formato de variable** | **Fuente**
| ------------------------------------- | ------------------------------------------------------------------ | -------------------- | ----------------------- | ----------------------- |
| **código de producto**                | Código identificador de producto                                   | `productId`          | Texto / String          | DWH                     | 
| **folio de venta**                    | Código identificador de folio de factura de venta                  | `folio`              | Texto / String          | DWH                     |
| **código de cliente**                 | Código identificador de cliente                                    | `clientId`           | Texto / String          | DWH                     |
| **categoría de producto**             | Categoría a la que pertenece el producto                           | `category`           | Texto / String          | ct_online2              |
| **sucursal**                          | Sucursal en la que se vendió el producto                           | `branch`             | Texto / String          | DWH                     |
| **estado**                            | Estado en el que se vendió el producto                             | `state`              | Texto / String          | DWH                     |
| **precio de producto**                | Precio por unidad de producto (pesos mexicanos)                    | `price`              | Texto / String          | DWH                     |
| **cantidad (producto)**               | Cantidad de unidades vendidas por factura del producto             | `quantity`           | Numérico / Entero       | DWH                     |
| **existencia (producto)**             | Cantidad de unidades en almacenamiento de producto por sucursal    | `existence`          | Array                   | CT_API_Publica/CT_Historico |
| **fecha de registro**                 | Fecha de registro de información de almacenamiento                 | `register_date`      | Fecha datetime64[ns] (YYYY-MM-DD) | CT_API_Publica/CT_Historico |
| **inventario (producto)**             | Cantidad total de unidades en almacenamiento de producto           | `total_stock`        | Numérico / Entero       | CT_API_Publica/CT_Historico |
| **ventas diarias (producto)**         | Cantidad de unidades vendidas por día del producto                 | `sales_day`          | Numérico / Entero       | DWH                     |
| **ingreso total (producto)**          | Ingreso neto obtenido por las ventas del producto                  | `income`             | Numérico / Decimal      | DWH                     |
| **costo (producto)**                  | Costo total de producción o adquisición del producto               | `cost`               | Numérico / Decimal      |  DWH/CT_Historico       |
| **fecha**                             | Fecha de la venta realizada                                        | `date`               | Fecha datetime64[ns] (YYYY-MM-DD) | DWH           |
| **mes**                               | Mes de la venta realizada                                          | `month`              | Texto / String          | DWH                     |
| **año**                               | Año de la venta realizada                                          | `year`               | Texto / String          | DWH                     |
