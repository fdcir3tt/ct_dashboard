# Esquema de colección : tbl_existenciaHistorial





| **Nombre**                            | **Descripción**                                                    | **Requerido**         | **Formato de variable** | **Fuente**                  |
| ------------------------------------- | ------------------------------------------------------------------ | -------------------- | ----------------------- | --------------------------- |
| `_id`                            | Identificador único del documento                                      | Sí          | ObjectId          | CT_API_Publica / tbl_existenciaHistorial |
| `productId`                            | Código identificador de producto                                       | Sí          | Texto / String          | CT_API_Publica / tbl_existencia |
| `active`                            |  Describe si el producto esta actualmente activo                                       | Sí          | Booleano          | CT_API_Publica / tbl_existencia |
| `units_stored`                            |  Cuántas unidades existen por almacen                                       | Sí          | Object          | CT_API_Publica / tbl_existencia |
| `date_stored`                            |  Fecha en la que se capturó y guardó la información en colección                                       | Sí          | datetime         | CT_API_Publica / tbl_existencia |
| `existenceId`                            |  Identificador único del documento del cual se extrajo la información                                      | Sí          |  ObjectId       | CT_API_Publica / tbl_existencia |
