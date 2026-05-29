<p align="left">
  <img src="https://tse2.mm.bing.net/th/id/OIP.7-vcHRuuctZh2w5FtJXKMgAAAA?cb=12&rs=1&pid=ImgDetMain&o=7&rm=3" alt="ct_logo" width="100">
</p>


# CT Forecasting Dashboard
[![Python][python-shield]][python-url]
[![Markdown][md-shield]][md-url]
[![Git][git-shield]][git-url]
[![Github][github-shield]][github-url]
[![Jupyter Notebooks][jupyter-shield]][jupyter-url]
[![PostgreSQL][postgres-shield]][postgres-url]
[![Airflow][airflow-shield]][airflow-url]
[![MLflow][mlflow-shield]][mlflow-url]
[![Pandas][pandas-shield]][pandas-url]
[![Podman][podman-shield]][podman-url]

[![Streamlit App][streamlit-shield]][streamlit-url]
[![Seaborn][seaborn-shield]][seaborn-url]

[postgres-shield]: https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white
[postgres-url]: https://www.postgresql.org/

[airflow-shield]: https://img.shields.io/badge/Apache%20Airflow-017CEE?style=for-the-badge&logo=apacheairflow&logoColor=white
[airflow-url]: https://airflow.apache.org/

[mlflow-shield]: https://img.shields.io/badge/MLflow-0194E2?style=for-the-badge&logo=mlflow&logoColor=white
[mlflow-url]: https://mlflow.org/

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

[jupyter-shield]: https://img.shields.io/badge/Jupyter-Notebook-orange?style=for-the-badge&logo=jupyter&logoColor=white
[jupyter-url]: https://jupyter.org/


[streamlit-shield]:https://img.shields.io/badge/-Streamlit-FF4B4B?style=flat&logo=streamlit&logoColor=white
[streamlit-url]:https://streamlit.io/

[seaborn-shield]:https://img.shields.io/badge/Seaborn-0.13.2-blue?logo=python&logoColor=red
[seaborn-url]:https://seaborn.pydata.org/




[Sitio del proyecto](https://fdcir3tt.github.io/ct_forecasting_site/)
## Descripción

Herramienta de análisis y visualización de la distribución de productos en las sucursales de CT International. El proyecto reemplaza el flujo de trabajo basado en Excel por un dashboard interactivo que centraliza la información de ventas, inventario y pronósticos, con el objetivo de agilizar la toma de decisiones diaria.

El sistema se divide en tres componentes principales, cada uno con responsabilidades bien definidas:

| Componente | Responsabilidad |
|------------|----------------|
| [`etl/`](etl/README.md) | Orquestación e ingestión de datos mediante pipelines de Apache Airflow |
| [`mlops/`](mlops/README.md) | Entrenamiento, evaluación y monitoreo de modelos de pronóstico |
| [`app/`](app/README.md) | Visualización interactiva del dashboard con Streamlit |

---

## Estructura

```
ct_dashboard/
├── app/          # Dashboard de visualización (Streamlit)
├── etl/          # Gestión de pipelines de datos (Airflow)
├── mlops/        # Entrenamiento y monitoreo de modelos (MLflow)
├── .dockerignore
├── .gitignore
├── license.md
└── README.md               


```
---

## Tech Stack

| Capa | Tecnología |
|------|------------|
| Lenguaje | Python 3.12 |
| Visualización | Streamlit, Seaborn 0.13.2 |
| Orquestación | Apache Airflow 2.9 |
| Experimentación | MLflow 3.10 |
| Procesamiento de datos | Pandas 2.3 |
| Base de datos | PostgreSQL 15 |
| Contenerización | Podman 5.4 + podman-compose 0.11 |

---

## Licencia

Este proyecto se distribuye bajo la licencia [MIT](license.md).
