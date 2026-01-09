FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV POETRY_HOME=/opt/poetry
ENV PATH="$POETRY_HOME/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV APP_HOSTNAME=ct_dashboard


RUN apt-get update && apt-get install -y \
    curl \
    gnupg2 \
    lsb-release \
    build-essential \
    pkg-config \
    unixodbc \
    unixodbc-dev \
    default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

# Agregar repositorio de Microsoft ODBC Driver
RUN curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > /usr/share/keyrings/microsoft.gpg && \
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" \
        > /etc/apt/sources.list.d/mssql-release.list

# Instalar ODBC Driver 17
RUN apt-get update && ACCEPT_EULA=Y apt-get install -y msodbcsql17 \
    && rm -rf /var/lib/apt/lists/*

# Instalar poetry 
RUN curl -sSL https://install.python-poetry.org | python3 -

WORKDIR /app

# Copiar solo archivos de dependencias
COPY pyproject.toml poetry.lock* ./

# Instalar dependencias SIN virtualenv
RUN poetry config virtualenvs.create false \
    && poetry install --no-root --no-interaction --no-ansi

COPY . .

EXPOSE 8501

CMD ["poetry", "run", "streamlit","run", "app.py", \
     "--server.address=0.0.0.0", \
     "--server.port=8501"]