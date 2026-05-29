# Dashboard de Ventas e Inventario
[![Python][python-shield]][python-url]
[![Markdown][md-shield]][md-url]
[![Git][git-shield]][git-url]
[![Github][github-shield]][github-url]
[![PostgreSQL][postgres-shield]][postgres-url]
[![Pandas][pandas-shield]][pandas-url]
[![Podman][podman-shield]][podman-url]

[![Streamlit App][streamlit-shield]][streamlit-url]
[![Seaborn][seaborn-shield]][seaborn-url]

[postgres-shield]: https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white
[postgres-url]: https://www.postgresql.org/

[pandas-shield]: https://img.shields.io/badge/Pandas-150458?style=for-the-badge&logo=pandas&logoColor=white
[pandas-url]: https://pandas.pydata.org/

[podman-shield]: https://img.shields.io/badge/Podman-892CA0?style=for-the-badge&logo=podman&logoColor=white
[podman-url]: https://podman.io/

[python-shield]: https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54
[python-url]: https://www.python.org/

[md-shield]: https://img.shields.io/badge/Markdown-000?style=for-the-badge&logo=markdown
[md-url]: https://www.markdownguide.org/

[git-shield]: https://img.shields.io/badge/GIT-E44C30?style=for-the-badge&logo=git&logoColor=white
[git-url]: https://git-scm.com/

[github-shield]: https://img.shields.io/badge/GitHub-100000?style=for-the-badge&logo=github&logoColor=white
[github-url]: https://github.com/


[streamlit-shield]:https://img.shields.io/badge/-Streamlit-FF4B4B?style=flat&logo=streamlit&logoColor=white
[streamlit-url]:https://streamlit.io/

[seaborn-shield]:https://img.shields.io/badge/Seaborn-0.13.2-blue?logo=python&logoColor=red
[seaborn-url]:https://seaborn.pydata.org/

Aplicación web construida con Streamlit para el monitoreo continuo de ventas e inventario de productos. Su objetivo es centralizar las visualizaciones clave que apoyan la toma de decisiones en el surtimiento de productos.

## Instalación

**Requisitos previos:** `podman >= 5.4` y `podman-compose >= 0.11`

1. Copia el archivo `compose.yml` en la raíz del proyecto.
2. Definir url de conexión a base de datos como variable de entorno `DASHBOARD_URL`
3. Levanta la aplicación:

```bash
podman compose up -d
```

### Actualización

```bash
podman compose down
podman compose up -d
```

---

```
podman compose up -d 
```

Para actualizar, uno simplemente ejecuta:
```
podman compose down 
podman compose up -d 
```

---

## Guía de Uso

Una vez iniciada la aplicación, accede a `http://<host>:8501`. Se mostrará por defecto la pestaña de **Ventas de Productos**.

### Filtros

#### Filtros de elemento

Permite analizar los datos tanto por productos individuales como por categorías. También es posible excluir las ventas atípicas del análisis.

<p align="left">
  <img src="references/examples/element_filters.png" alt="Filtros de elemento" width="300">
</p>

#### Filtros de análisis

Aquí se seleccionan los productos a comparar (hasta cuatro en la gráfica de ventas), el producto o categoría principal, la sucursal y el período de análisis.

<p align="left">
  <img src="references/examples/filters.png" alt="Filtros de análisis" width="300">
</p>

#### Información del elemento

En el panel izquierdo se despliega la ficha del elemento seleccionado (producto o categoría), que incluye: código, categoría, costo unitario, precio promedio por unidad y clientes frecuentes.

<p align="left">
  <img src="references/examples/info_element.png" alt="Información del elemento" width="400">
</p>

---

### Gráficas

#### Ventas e Inventario diario

Muestra las unidades vendidas por día (pestaña de Ventas) o la existencia diaria (pestaña de Inventario), tanto a nivel de sucursal como a nivel global, para comparar el comportamiento particular con la tendencia general.

<p align="left">
  <img src="references/examples/sales.png" alt="Gráfica de ventas" width="500">
  <img src="references/examples/inventory.png" alt="Gráfica de inventario" width="500">
</p>

#### Frecuencia de pedidos

Indica con qué frecuencia se realizan pedidos de determinada cantidad de unidades del producto dentro del período seleccionado.

<p align="left">
  <img src="references/examples/freq_plots.png" alt="Gráfica de frecuencia" width="600">
</p>

#### KPIs

Concentra los indicadores clave para la toma de decisiones: unidades vendidas, costo total y ganancia total del elemento seleccionado.

<p align="left">
  <img src="references/examples/kpis_inv.png" alt="KPIs de inventario" width="340">
  <img src="references/examples/kpis_sales.png" alt="KPIs de ventas" width="500">
</p>

#### Mapa de calor

Visualiza la actividad de ventas o inventario por zona geográfica, facilitando identificar qué sucursales requieren mayor stock ante posibles picos de demanda.

<p align="left">
  <img src="references/examples/heat_map.png" alt="Mapa de calor" width="400">
</p>

#### Gráfica de prioridades

Muestra los productos con mayor prioridad de surtimiento junto con su volumen de ventas en el período. La prioridad se determina con base en el valor aportado al total mensual, usando el costo del producto como criterio (al ser un valor generalmente estable).

<p align="left">
  <img src="references/examples/priorities.png" alt="Gráfica de prioridades" width="400">
</p>

---

## Demo

<p align="left">
  <img src="references/examples/demo.gif" alt="Demo de la aplicación" width="700">
</p>

---

## Tech Stack

| Capa | Tecnología |
|------|------------|
| Frontend / Visualización | Streamlit |
| Contenerización | Podman + podman-compose |
| Lenguaje | Python |
| Bases de datos | PostgreSQL 15.0, PostGIS 15.4 |