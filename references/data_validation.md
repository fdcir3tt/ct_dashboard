# Validación de datos

Para obtener valor del dashboard, necesita tener confianza en que los datos plasmados/utilizados reflejen la realidad. Por esto, es importante tener criterios de validación de estos a la mano. 

## Validaciones básicas

**Registros no nulos :**

Para nuestro caso, los registros nulos no nos sirven para nada por el momento. Es por ello que los filtraremos del conjunto final de datos. Como estaremos implementando [`dask`](https://docs.dask.org/en/stable/), para llevar a cabo esta tarea utilizaremos el método `dask.dataframe.DataFrame.isna()` para detectar valores nulos y `dask.dataframe.DataFrame.dropna()` para eliminarlos.

**Formatos consistentes de columnas :**

Se utilizará el método `dask.dataframe.DataFrame.dtypes` para confirmar que los formatos sean los adecuados.  







## Rangos y Duplicidad

**Suma de ventas por producto total deben ser igual a la suma de categorias total :**

Esta validación consiste en verificar si se hace la agrupación/separación entre productos y categorías correctamente. Para ello, se compara la suma de ventas a nivel producto con la suma de ventas a nivel categoría. 

**Precios,costos, cantidades positivas :**

Se revisará que columnas como `price` ,`cost`, `sales_{frequency}` caigan dentro de su rango lógico. 

**Precio debe ser mayor a costo :**

Para que nuestro conjunto de datos refleje información que tenga sentido, una debe ser que el precio de producto sea mayor a su costo. 


**Fechas dentro de 2020 y actualidad**

A nosotros y los usuarios solo nos interesan fechas que se encuentren dentro del periodo del 2020 hasta la actualidad.


**Velocidad de venta diaria debe ser menor o igual a la venta diaria** 

No son validas las velocidades de venta diaria que sean mayores a la venta diaria. 
 

**Cantidad de folios debe ser igual a la cantidad de registros :** 

Esto es para probar la unicidad de la columna de `folio`.


