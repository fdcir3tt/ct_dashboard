import pandas as pd
import os
import datetime
import logging
import numpy as np

from json import JSONDecodeError
from dotenv import load_dotenv
from data_loader import load_raw_exchange_rates,load_exchange_rates,update_exchange_rates,get_usd_to_mxn
from preprocess import process_exchange_rates

# -----------------------------------------------------------
# SETUP 
# -----------------------------------------------------------

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



def log_exchange_rate_update(status: bool,meta_data: dict,logger: logging.Logger = logger,):
    msg = (
        "Stats update exchange rates | "
        f"status={status} "
        f"prev_rate={meta_data.get('previous_rate')} "
        f"fetched_at={meta_data.get('API_call_time')} "
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



def main():
    meta_data = {}
    file_exists = os.path.exists("data/raw/usd_mxn_rates.parquet")
    if file_exists:
        df = pd.read_parquet("data/raw/usd_mxn_rates.parquet")
        previous_rate= df.iloc[-1]
    else:
        df = load_exchange_rates()
        if df is not None:
            meta_data["fallback_type"] = "estimated" 
            meta_data["fallback_source_date"] = datetime.datetime.today()
            previous_rate= df.iloc[-1]
        else:
            raw_df=load_raw_exchange_rates()
            process_exchange_rates(data=raw_df)
            df = load_exchange_rates()

            meta_data["fallback_type"] = "estimated" 
            meta_data["fallback_source_date"] = datetime.datetime.today()
            previous_rate= df.iloc[-1]

    # Llamada a API de conversiones
    fetched_at = datetime.datetime.today()
    
    rate = get_usd_to_mxn(logger=logger)

    # Actualización 
    if rate:
        meta_data["fetched_at"]=fetched_at
        if file_exists:
            df = pd.read_parquet("data/raw/usd_mxn_rates.parquet")
        else:
             df = load_exchange_rates()
        updated = update_exchange_rates(logger=logger,rates_dataframe=df)

    else: 
        if file_exists:
            df = pd.read_parquet("data/raw/usd_mxn_rates.parquet")
        else:
             df = load_exchange_rates()
        rate = np.mean([ df["exchange_rate"].iloc[-1],df["exchange_rate"].iloc[-2] ])
        meta_data["fallback_type"] = "estimated" 
        meta_data["fallback_source_date"] = df["date"].iloc[-1]
        updated = update_exchange_rates(logger=logger,rates_dataframe=df,rate=rate)

    # Loggeo
    updated.to_parquet("data/raw/usd_mxn_rates.parquet")
    meta_data["prev_rate"]=previous_rate
    meta_data["status"]=True
    log_exchange_rate_update(status=True,meta_data=meta_data)




if __name__ == "__main__":
    main()