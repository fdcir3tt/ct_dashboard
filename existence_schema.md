# Esquema de colección : tbl_existenciasHistorial





| **Nombre**                            | **Nombre en tabla** | **Descripción**                                                    | **Requerido**         | **Formato de variable** | **Fuente**                  |
| ------------------------------------- | ------------------------------------- | ------------------------------------------------------------------ | -------------------- | ----------------------- | --------------------------- |
| `_id`                            | _id | Identificador único del documento                                      | Sí          | ObjectId          | CT_API_Publica / tbl_existenciasHistorial |
| `existenceId`                            | existenciaId| Identificador único del documento del cual se extrajo la información                                      | Sí          |  ObjectId       | CT_API_Publica / tbl_existencias |
| `productId`                            |codigo | Código identificador de producto                                       | Sí          | Texto / String          | CT_API_Publica / tbl_existencias |
| `active`                            |activo|  Describe si el producto esta actualmente activo                                       | Sí          | Array         | CT_API_Publica / tbl_existencias |
| `cost`                            |costo|  Cuántas unidades existen por almacen                                       | Sí          | Array         | DWH / CAT_ARTICULOS |
| `units_stored`                            |almacenes|  Cuántas unidades existen por almacen                                       | Sí          | Array           | CT_API_Publica / tbl_existencias |
| `date_stored`                            |fechaRegistro|  Fecha en la que se capturó y guardó la información en colección                                       | Sí          | datetime         | CT_API_Publica / tbl_existenciasHistorial |
| `date_updae`                            |fechaUpdate|  Fecha en la que se actualizó la información del documento en la colección                                       | Sí          | datetime         | CT_API_Publica / tbl_existenciasHistorial |

