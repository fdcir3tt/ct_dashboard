# ========================
# Stage 1: Build stage
# ========================
FROM python:3.12-slim AS builder

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV POETRY_HOME=/opt/poetry
ENV PATH="$POETRY_HOME/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
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

# Install Microsoft ODBC Driver
RUN curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > /usr/share/keyrings/microsoft.gpg && \
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" > /etc/apt/sources.list.d/mssql-release.list && \
    apt-get update && ACCEPT_EULA=Y apt-get install -y msodbcsql17 \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Set the working directory
WORKDIR /app

# Copy only dependency files first to leverage Docker cache
COPY pyproject.toml poetry.lock* /app/

# Install dependencies without creating virtualenv
RUN poetry config virtualenvs.create false \
    && poetry install --no-root --no-interaction --no-ansi

# Copy the rest of the app code
COPY app/ /app/

# ========================
# Stage 2: Runtime stage
# ========================
FROM python:3.12-slim AS final

# Set environment variables for runtime
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV POETRY_HOME=/opt/poetry
ENV PATH="$POETRY_HOME/bin:$PATH"

# Install system dependencies for runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    unixodbc \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy Poetry and Python packages from the builder stage
COPY --from=builder /opt/poetry /opt/poetry
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages

# Copy the app code from the builder stage
COPY --from=builder /app/ /app/

# Expose the port Streamlit will run on
EXPOSE 8501

# Combine both script executions (exchange rates update + shapefile extraction) 
# with Streamlit running in a single CMD
CMD PYTHONPATH=/app python scripts/exchange_rates_update.py && \
    PYTHONPATH=/app python scripts/shapefile_extraction.py && \
    PYTHONPATH=/app streamlit run app.py --server.address=0.0.0.0 --server.port=8501

