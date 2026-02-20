FROM python:3.12-slim 

# Variables de entorno
ENV DEBIAN_FRONTEND=noninteractive
ENV POETRY_HOME=/opt/poetry
ENV PATH="$POETRY_HOME/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Instalar dependencias de sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    cron \
    gnupg2 \
    lsb-release \
    build-essential \
    pkg-config \
    unixodbc \
    unixodbc-dev \
    default-libmysqlclient-dev \
    libssl-dev \
    libffi-dev \
    unixodbc-dev \
    libpq-dev \
    python3-dev \
    gcc \
    libssl-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Instalar Microsoft ODBC Driver
RUN curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > /usr/share/keyrings/microsoft.gpg && \
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" > /etc/apt/sources.list.d/mssql-release.list && \
    apt-get update && ACCEPT_EULA=Y apt-get install -y msodbcsql17 \
    && rm -rf /var/lib/apt/lists/*


RUN curl -sSL https://install.python-poetry.org | python3 -


WORKDIR /app


COPY app/pyproject.toml app/poetry.lock* /app/ 
COPY app/ /app/ 
COPY data_update /etc/cron.d/dashboard_data_update

RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi


RUN chmod 0644 /etc/cron.d/dashboard_data_update \
    && crontab /etc/cron.d/dashboard_data_update \


EXPOSE 8501
CMD cron && \ 
    PYTHONPATH=/app python scripts/etl_pipeline.py && \
    PYTHONPATH=/app streamlit run app.py --server.address=0.0.0.0 --server.port=8501

