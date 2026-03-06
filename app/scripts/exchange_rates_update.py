import pandas as pd
import os
import datetime
import logging
import numpy as np
import warnings


from dotenv import load_dotenv
from dashboard.data_loader import load_raw_exchange_rates,load_exchange_rates,update_exchange_rates,get_usd_to_mxn
from dashboard.preprocess import process_exchange_rates

# -----------------------------------------------------------
# SETUP 
# -----------------------------------------------------------
warnings.filterwarnings('ignore')
load_dotenv()

EXCHANGE_API_KEY = os.getenv("EXCHANGE_API_KEY")
LOG_DIR = "log"

os.makedirs(LOG_DIR, exist_ok=True)
log_path = "log/exchange_rates.log"

logging.basicConfig(
    filename=log_path,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def is_up_to_date():
    file_exists = os.path.exists("data/raw/usd_mxn_rates.parquet")
    if file_exists:
        df = pd.read_parquet("data/raw/usd_mxn_rates.parquet")
        previous_rate= df['exchange_rate'].iloc[-1]
        latest_date = df.index.max()

    else:
        return False
    
    rate = get_usd_to_mxn(logger=logger)
    if rate is None:
        return False
    else:
        return (previous_rate==rate)&(datetime.date.today()==latest_date)
    
def log_exchange_rate_update(status: bool,meta_data: dict,logger: logging.Logger = logger,):
    msg = (
        "Stats update exchange rates | "
        f"status={status} "
        f"prev_rate={meta_data.get('previous_rate')} "
        f"fetched_at={meta_data.get('fetched_at')} "
    )

    if meta_data.get("errors"):
        logger.error(
            msg,
            extra={"errors": meta_data["errors"]},
        )
    elif meta_data.get("fallback_type"):
        logger.info( msg +
        f"fallback_type={meta_data.get('fallback_type')} "+
        f"fallback_source_date={meta_data.get('fallback_source_date')}"
        )
    else:
        logger.info(msg)

def get_local_dataframe():
    if os.path.exists("data/raw/usd_mxn_rates.parquet"):
        return pd.read_parquet("data/raw/usd_mxn_rates.parquet")
    return load_exchange_rates()

def main():

    df = get_local_dataframe()

    if df is not None and is_up_to_date():
        print("Conversiones ya están actualizadas!")
        return

    previous_rate = df["exchange_rate"].iloc[-1]

    try:
        rate = get_usd_to_mxn(logger=logger)
    except Exception as e:
        logger.error(e)
        rate = None

    if rate is None:
        print("No se pudo extraer un valor de conversion")
        rate = np.mean(df["exchange_rate"].tail(2))
        fallback = True
    else:
        fallback = False

    updated = update_exchange_rates(
        logger=logger,
        rates_dataframe=df,
        rate=rate
    )

    updated.to_parquet("data/raw/usd_mxn_rates.parquet")

    meta_data = {
        "previous_rate": previous_rate,
        "fetched_at": datetime.datetime.today(),
    }

    if fallback:
        meta_data["fallback_type"] = "estimated"

    log_exchange_rate_update(status=True,meta_data=meta_data)

    raw_df = load_raw_exchange_rates()

    rates_df = pd.read_parquet("data/raw/usd_mxn_rates.parquet")
    
    process_exchange_rates(
        data=raw_df,
        raw_rates=rates_df,
        logger=logger
    )



if __name__ == "__main__":
    main()