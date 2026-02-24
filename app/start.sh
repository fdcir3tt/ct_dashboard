#!/bin/bash
export PYTHONPATH=/app

# Ejecutar en el fondo
python scripts/etl_scheduler.py &

# Ejecutar una vez al iniciar aplicación
python scripts/etl_pipeline.py

streamlit run app.py --server.address=0.0.0.0 --server.port=8501