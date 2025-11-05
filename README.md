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
│
├── app.py                    # Punto de entrada principal (main)
│
├── pages/                    # Subcarpeta para las páginas (si usas multipage)
│   ├── 1_Dashboard_General.py
│   ├── 2_Análisis_Detallado.py
│   └── 3_Ajustes.py
│
├── data/                     # Datos locales (CSV, JSON, etc.)
│   ├── ventas.csv
│   └── clientes.csv
│
├── src/                      # Código fuente (módulos auxiliares)
│   ├── __init__.py
│   ├── data_loader.py        # Funciones para cargar datos
│   ├── preprocess.py         # Limpieza y transformación de datos
│   ├── charts.py             # Funciones para generar gráficos
│   └── utils.py              # Funciones de utilidad (colores, formatos, etc.)
│
├── assets/                   # Recursos estáticos (imágenes, CSS, logos)
│   ├── logo.png
│   └── style.css
│
├── requirements.txt          # Dependencias del proyecto
├── .env
├── license.md
├── poetry.lock
├── pyproject.toml 
└── README.md                 # Descripción del proyecto

```

## Tech Stack

- **Lenguaje** : Python 3.12
- **Bases de datos** :Microsoft SQL Server,MongoDB, MySQL (mysql-connector-python)
- **Análisis de Datos y Reportes** : Pandas



## Licencia
Este proyecto se rige bajo la licencia de MIT.
