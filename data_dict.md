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

| **Nombre**                            | **Descripción**                                                    | **Variable**         | **Formato de variable** |
| ------------------------------------- | ------------------------------------------------------------------ | -------------------- | ----------------------- |
| **código**                            | Código identificador de producto                                       | `productId`          | Texto / String          |
| **código sustituto**                  | Código del producto que reemplazará al actual                      | `productId_subst`    | Texto / String          |
| **categoría**                         | Categoría a la que pertenece el producto                           | `category`           | Texto / String          |
| **ventas diarias (producto)**         | Cantidad de unidades vendidas por día del producto                 | `sales_day`          | Numérico / Entero       |
| **ventas mensuales (producto)**       | Cantidad total de unidades vendidas en el mes                      | `sales_month`        | Numérico / Entero       |
| **ganancia total (producto)**         | Ingreso neto obtenido por las ventas del producto                  | `total_profit`       | Numérico / Decimal      |
| **costo total (producto)**            | Costo total de producción o adquisición del producto               | `total_cost`         | Numérico / Decimal      |
| **cliente frecuente**                 | Cliente que compra con mayor recurrencia el producto               | `freq_client`        | Texto / String          |
| **frecuencia de venta (producto)**    | Promedio de días entre cada venta del producto                     | `sales_freq`         | Numérico / Decimal      |
| **fecha de última venta (producto)**  | Fecha de la venta más reciente del producto                        | `last_sale_date`     | Fecha (YYYY-MM-DD)      |
| **mes**  | Mes de la venta realizada                         | `month`     | Texto / String      |
| **año**  | Año de la venta realizada                        | `year`     | Texto / String      |
| **ventas diarias (categoría)**        | Total de unidades vendidas por día dentro de la categoría          | `cat_sales_day`      | Numérico / Entero       |
| **ventas mensuales (categoría)**      | Total de unidades vendidas en el mes dentro de la categoría        | `cat_sales_month`    | Numérico / Entero       |
| **ganancia total (categoría)**        | Ingreso neto total obtenido de todos los productos de la categoría | `total_cat_profit`   | Numérico / Decimal      |
| **costo total (categoría)**           | Suma total de los costos de los productos dentro de la categoría   | `total_cat_cost`     | Numérico / Decimal      |
| **fecha de última venta (categoría)** | Fecha de la venta más reciente dentro de la categoría              | `last_cat_sale_date` | Fecha (YYYY-MM-DD)      |
| **frecuencia de venta (categoría)**   | Promedio de días entre ventas de la categoría                      | `cat_sales_freq`     | Numérico / Decimal      |

