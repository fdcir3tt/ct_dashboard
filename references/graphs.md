# Gráficos clave



## Ventas 

**Objetivo:** Esta gráfica quiere visualizar el comportamiento de las ventas de los productos seleccionados,(máximo 4 productos), para lograr observar posibles tendencias y estacionalidades dentro del periodo seleccionado. 

**Variables:** Se toman en cuenta las variables `date` y `sales_{frecuencia}` como los ejes horizontal y vertical respectivamente donde frecuencia indica si se trata de ventas diarias,semanales o mensuales. 

**Ejemplo:**
<p align="center">
  <img src="../plots/almacen_ventas.png?updated=1" alt="ventas" width="1000">
</p>

## Rápidez de Ventas

**Objetivo:** Se tiene en mente comparar la velocidad de venta de los productos seleccionados,(máximo 4 productos), para ayudar predecir la demanda de dichos productos.

**Variables:** Se toman en cuenta las variables `date` y `sales_velocity_{frequency}` como los ejes horizontal y vertical respectivamente donde `frecuency` indica si se trata de ventas diarias,semanales o mensuales.

**Ejemplo:**
<p align="center">
  <img src="../plots/almacen_v_rapidez_ventas.png?updated=1" alt="rapidez_ventas" width="1000">
</p>

## Histograma de ventas

**Objetivo:** Queremos visualizar en general la frecuencia de las cantidades pedidas del producto seleccionado. Sólo se puede seleccionar uno a la vez. Esto ayuda tener una mejor idea en cuanto el umbral mínimo de productos que deben haber en almacen para evitar perder una venta potencial.

**Variables:** Se toman en cuenta las variables `date` y `quantity` como los ejes horizontal y vertical respectivamente.

**Ejemplo:**
<p align="center">
  <img src="../plots/hist_ventas_prod.png?updated=1" alt="histograma" width="1000">
</p>


## Mapa de Calor de Ventas
**Objetivo:** Visualizar áreas geográficas en donde hay más actividad de ventas. Ayuda identificar qué sucursales requieren mantener más productos en almacen por posibles ventas futuras.

**Variables:** Se utilizan las variables `state`,`quantity` y el archivo _gadm41_MEX_shp/gadm41_MEX_1.shp_ para realizar el mapa de calor. La variable `quantity` se suma por estado y se hace una unión entre tablas sobre `state`.  

**Ejemplo:**
<p align="center">
  <img src="../plots/heatmap_ventas_mexico.png?updated=1" alt="dashboard1" width="1000" >
</p>

## KPIs

**Objetivo:** Tener a la mano valores claves en la toma de decisiones relacionadas al surtimiento de productos. Los valores que consideramos útiles fueron las ventas totales,costo total, la ganancia total, y el cociente de inventario del producto seleccionado,(sólo uno a la vez).


**Variables:** Estos son los KPIs en cuestión y el cómo se obtienen: 

- `total_sales` : Se suman todos los valores de `quantity` 

- `total_profit` : Se suman todos los valores de `profit` 

- `total_cost` : Se multiplica `cost` por `total_sales` 

- `inventory_t_ratio` : Se divide `total_cost` entre el valor promedio de inventario del producto seleccionado. 



## Ventas por producto

**Objetivo:** Visualizar productos con prioridad junto con la cantidad de ventas que aportaron durante el periodo. El criterio de prioridad que se utiliza para asignarle magnitud de prioridad a cada producto es en base cuanto valor aporta al valor total del més.

**Variables:** Se utilizaron las variables `date`,`quantity`,`cost` para crear las características: 

- `cost` : Costo del producto 

- `total_sales` : Se suman todos los valores de `quantity` por producto agrupado

- `annual_value` : Multiplicación de los valores de `total_sales` y `cost`

- `cummulative_val`: Se ordena el dataframe de mayor a menor valor de `annual_value` y se suma cumulativamente `annual_value` entre el total de este mismo.

- `priority`: Se le aplica un método de clasificación a `cummulative_val`

**Ejemplo:**
<p align="center">
  <img src="../plots/productos_abc_chart.png?updated=1" alt="dashboard1" width="1000">
</p>


## Ventas por categoría

**Objetivo:** Mismo objetivo que el de ventas por producto, mismo método. Lo único que cambía es como se agrupan los datos para generar las características. 

**Ejemplo:**
<p align="center">
  <img src="../plots/categorias_abc_chart.png?updated=1" alt="dashboard1" width="1000">
</p>