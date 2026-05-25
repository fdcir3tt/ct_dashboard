FROM apache/airflow:2.9.3

ENV POETRY_HOME=/opt/poetry
ENV PATH="$POETRY_HOME/bin:$PATH"
USER root

RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    curl \
    default-libmysqlclient-dev\
    pkg-config \
    && apt-get clean

RUN curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > /usr/share/keyrings/microsoft.gpg && \
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" > /etc/apt/sources.list.d/mssql-release.list && \
    apt-get update && ACCEPT_EULA=Y apt-get install -y msodbcsql17 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml poetry.lock* /opt/airflow/

RUN curl -sSL https://install.python-poetry.org | python3 - \
    && poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --without dev,spark \
    && rm -rf $POETRY_HOME
    
USER root
COPY . /opt/airflow
RUN chown -R airflow: /opt/airflow

USER airflow
RUN pip install asyncpg

