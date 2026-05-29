# MLOps de Entrenamiento y Monitoreo de Modelos 
[![Python][python-shield]][python-url]
[![Markdown][md-shield]][md-url]
[![Git][git-shield]][git-url]
[![Github][github-shield]][github-url]
[![Jupyter Notebooks][jupyter-shield]][jupyter-url]
[![MLflow][mlflow-shield]][mlflow-url]
[![Pandas][pandas-shield]][pandas-url]




[mlflow-shield]: https://img.shields.io/badge/MLflow-0194E2?style=for-the-badge&logo=mlflow&logoColor=white
[mlflow-url]: https://mlflow.org/

[pandas-shield]: https://img.shields.io/badge/Pandas-150458?style=for-the-badge&logo=pandas&logoColor=white
[pandas-url]: https://pandas.pydata.org/

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

[seaborn-shield]:https://img.shields.io/badge/Seaborn-0.13.2-blue?logo=python&logoColor=red
[seaborn-url]:https://seaborn.pydata.org/


Ecosistema de trabajo reproducible y monitoreable para entrenar, evaluar y actualizar modelos de manera sistemática. Facilita la mejora continua del rendimiento y permite detectar oportunamente problemas como degradación del modelo, cambios en la distribución de los datos o fallos en los procesos de ingestión.

---

## Instalación

**Requisitos previos:** `poetry >= 2.3`

1. Clona el repositorio `mlops`.
2. Instala las dependencias:

```bash
poetry install -e
```

3. Levanta la interfaz de MLflow:

```bash
poetry run mlflow ui
```

---

## Guía de Uso

Una vez iniciada la UI, accede a `http://<host>:5000` desde cualquier navegador.

### Comparación de corridas

Desde la vista principal es posible visualizar y comparar las métricas registradas en cada corrida de entrenamiento. Actualmente se monitorean:

- **MSE** — Mean Squared Error
- **RMSE** — Root Mean Squared Error
- **MAE** — Mean Absolute Error

<p align="left">
  <img src="references/examples/train_runs.png" alt="Vista de corridas de entrenamiento" width="500">
</p>

### Detalle de una corrida

Al acceder a una corrida específica se pueden consultar los parámetros de entrenamiento, los datasets utilizados, artefactos generados y demás metadatos registrados.

<p align="left">
  <img src="references/examples/run_example.png" alt="Ejemplo de corrida individual" width="500">
</p>

---

## Demo

<p align="left">
  <img src="references/examples/demo.gif" alt="Demo del pipeline MLOps" width="700">
</p>

---

## Tech Stack

| Capa | Tecnología |
|------|------------|
| Experimentación y monitoreo | MLflow 3.10 |
| Gestión de dependencias | Poetry 2.3|
| Procesamiento de datos | Pandas 2.3 |
| Lenguaje | Python 3.12 |



