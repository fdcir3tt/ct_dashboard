#!/bin/bash
set -e

podman network create dashboard-net 2>/dev/null || true
chmod -R 755 ./orchestrations ./pipelines ./common ../data
chcon -R -t container_file_t -l s0 ./orchestrations ./pipelines ./common ../data

podman-compose up -d postgres
echo "Esperando que postgres esté listo..."
until podman exec postgres pg_isready -U airflow 2>/dev/null; do
  echo "  ...esperando"
  sleep 3
done
echo "inicializando Airflow DB..."
podman-compose up airflow-init
sleep 5
echo "Levantando scheduler primero..."
podman-compose up -d scheduler
sleep 5
echo "Arreglando permisos de logs..."
podman exec scheduler chmod -R 777 /opt/airflow/logs


echo "Levantando webserver y scheduler ..."
podman-compose up -d webserver