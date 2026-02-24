import subprocess
import schedule
import time
from datetime import datetime, timedelta

def run_etl():
    print(f"ETL empezado a {datetime.now()}")
    subprocess.run(['python', 'scripts/etl_pipeline.py'])
    print(f"ETL terminado a {datetime.now()}")

MAX_SLEEP = 3600 * 6

schedule.every().day.at("17:15").do(run_etl)

while True:
    now = datetime.now()
    schedule.run_pending()

    # Encontrar siguiente corrida pendiente
    next_run_times = [job.next_run for job in schedule.jobs if job.next_run]
    
    if next_run_times:
        next_run = min(next_run_times)
        sleep_seconds = (next_run - now).total_seconds()
        # Esperar hasta próxima corrida
        time.sleep( max( 0,min(sleep_seconds, MAX_SLEEP) ) )
    else:
        time.sleep(60)