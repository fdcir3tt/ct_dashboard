FROM apache/airflow:2.9.3

ENV POETRY_HOME=/opt/poetry
ENV PATH="$POETRY_HOME/bin:$PATH"
USER root

RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    curl \
    && apt-get clean


COPY pyproject.toml poetry.lock* /opt/airflow/

RUN curl -sSL https://install.python-poetry.org | python3 - \
    && poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --without dev,spark \
    && rm -rf $POETRY_HOME
    
RUN chown -R airflow: /opt/airflow

USER airflow
RUN pip install asyncpg
COPY . /opt/airflow

