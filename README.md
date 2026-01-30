<p align="left">
  <img src="https://tse2.mm.bing.net/th/id/OIP.7-vcHRuuctZh2w5FtJXKMgAAAA?cb=12&rs=1&pid=ImgDetMain&o=7&rm=3" alt="ct_logo" width="100">
</p>


# Dashboard Inventario
[![Python][python-shield]][python-url]
[![Markdown][md-shield]][md-url]
[![Git][git-shield]][git-url]
[![Github][github-shield]][github-url]

[![Jupyter Notebooks][jupyter-shield]][jupyter-url]

[![Streamlit App][streamlit-shield]][streamlit-url]
[![Seaborn][seaborn-shield]][seaborn-url]

[python-shield]: https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54
[python-url]: https://www.python.org/

[md-shield]: https://img.shields.io/badge/Markdown-000?style=for-the-badge&logo=markdown
[md-url]: https://www.markdownguide.org/

[git-shield]: https://img.shields.io/badge/GIT-E44C30?style=for-the-badge&logo=git&logoColor=white
[git-url]: https://git-scm.com/

[github-shield]: https://img.shields.io/badge/GitHub-100000?style=for-the-badge&logo=github&logoColor=white
[github-url]: https://github.com/

[jupyter-shield]: https://img.shields.io/badge/Jupyter-Notebook-orange?style=for-the-badge&logo=jupyter&logoColor=white
[jupyter-url]: https://jupyter.org/


[streamlit-shield]:https://static.streamlit.io/badges/streamlit_badge_black_red.svg
[streamlit-url]:https://streamlit.io/

[seaborn-shield]:https://img.shields.io/badge/Seaborn-0.13.2-blue?logo=python&logoColor=red
[seaborn-url]:https://seaborn.pydata.org/





## Objetivos del proyecto

El objetivo de este proyecto es visualizar la distribución de productos en las sucursales de CT International. Actualmente, la empresa gestiona el aspecto logístico mediante archivos de Excel. Se busca optimizar esta tarea mediante una herramienta intuitiva que permita visualizar la información de manera más eficiente. El éxito del proyecto se evaluará en función de la capacidad del dashboard para proporcionar información valiosa a los usuarios de forma diaria.

## Estructura

```
ct_dashboard/
.
├── app                           # Entorno de aplicación
│   │
│   ├── assets                    # Recursos estáticos (imágenes, CSS, logos)
│   │   ├── logo.png              
│   │   └── styles.css            
│   │
│   ├── data
│   │   ├── processed
│   │   │   ├── conversion_usd_mxn.parquet   # Datos de conversion procesados
│   │   │   └── facturas_ventas.parquet      # Datos de facturas de venta procesados
│   │   │
│   │   └── raw
│   │       ├── categorias.parquet            
│   │       ├── codigos_productos.parquet     
│   │       ├── facturas.parquet              
│   │       ├── historical_data_usd_mxn_2008-12-31_to_2026-01-20.csv  # Datos históricos de conversión de moneda
│   │       │                                
│   │       ├── productos.parquet             
│   │       ├── usd_mxn_rates.parquet          # Datos actualizados de conversión de moneda
│   │       │
│   │       └── gadm41_MEX_shp                 # Datos geográficos de México
│   │           
│   │
│   ├── log
│   │   ├── exchange_rates.log      
│   │   └── historic_stats.log      
│   │
│   ├── scripts
│   │   ├── exchange_rates_update.py 
│   │   ├── ingest.py               
│   │   ├── pipeline.py              # ETL pipeline
│   │   └── shapefile_extraction.py 
│   │
│   ├── src                          # Código fuente (módulos auxiliares)
│   │   └── ct_sales_dashboard
│   │       ├── data_loader.py       # Carga de datos
│   │       ├── graphs.py            # Gráficas y lógica de visualización
│   │       └── preprocess.py        # Limpieza y procesamiento de datos crudos
│   │
│   ├── tests
│   │    ├── test_data_loader.py      
│   │    ├── test_graphs.py           
│   │    ├── test_ingest.py           
│   │    └── validation_test.py       # Validación de datos 
│   │
│   ├── .env                      # Variables de entorno
│   ├── app.py                    # Punto de entrada principal (main)
│   ├── Dockerfile                
│   ├── poetry.lock               # Dependencias de proyecto
│   ├── pyproject.toml            
│   ├── pytest.ini                
│   └── states_dict.json          # Configuración de región/estado
│
├── references
│    ├── data_dict.md                 
│    ├── data_validation.md           # Reglas/criterios de validación de datos
│    ├── existence_schema.md          # Esquema de tabla de historial de existencias de productos
│    ├── graphs.md                    # Documentación acerca de gráficas y visualización
│    ├── links.md                     # Enlaces a referencias externas
│    └── other                        
│ 
├── .dockerignore                 
├── .gitignore                  
├── license.md                   
└── README.md                     



```

## Tech Stack

- **Lenguaje** : Python 3.12
- **Bases de datos** :Microsoft SQL Server,MongoDB, MySQL (mysql-connector-python)
- **Análisis de Datos y Reportes** : Pandas



## Licencia
Este proyecto se rige bajo la licencia de MIT.
