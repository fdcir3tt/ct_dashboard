# Diccionario de Datos



## Ventas

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
| **fecha**                             | Fecha de la venta realizada                                        | `date`               | Fecha datetime64[ns] (YYYY-MM-DD) | DWH           |


## Inventario

| **Nombre**                            | **Descripción**                                                    | **Variable**         | **Formato de variable** | **Fuente**
| ------------------------------------- | ------------------------------------------------------------------ | -------------------- | ----------------------- | ----------------------- |
| **código de producto**                | Código identificador de producto                                   | `productId`          | Texto / String          | DWH                     | 
| **existencia (producto)**             | Cantidad de unidades en almacenamiento de producto por sucursal    | `existence`          | Array                   | CT_API_Publica/CT_Historico |
| **fecha de registro**                 | Fecha de registro de información de almacenamiento                 | `register_date`      | Fecha datetime64[ns] (YYYY-MM-DD) | CT_API_Publica/CT_Historico |
| **inventario (producto)**             | Cantidad total de unidades en almacenamiento de producto           | `total_stock`        | Numérico / Entero       | CT_API_Publica/CT_Historico |
| **ingreso total (producto)**          | Ingreso neto obtenido por las ventas del producto                  | `income`             | Numérico / Decimal      | DWH                     |
| **costo (producto)**                  | Costo total de producción o adquisición del producto               | `cost`               | Numérico / Decimal      |  DWH/CT_Historico       |

