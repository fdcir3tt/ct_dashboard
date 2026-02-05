import os
import subprocess
from ct_sales_dashboard.data_loader import *
from ct_sales_dashboard.preprocess import *


def main():
    
# -----------------------------------------------------------
# ACTUALIZAR DATOS
# -----------------------------------------------------------
    if ( not os.path.exists("data/raw/gadm41_MEX_shp") ):
        subprocess.run(["python", "scripts/shapefile_extraction.py"])
    subprocess.run(["python", "scripts/ingest.py"])
    subprocess.run(["python", "scripts/exchange_rates_update.py"])

# -----------------------------------------------------------
# CARGAR DATOS
# -----------------------------------------------------------

    invoices = load_invoices()

    product_codes =load_product_codes()
    exchange_rates = load_exchange_rates()

    branches = load_branches()
    categories = load_categories()
    products = load_products()


    process_data (invoices,
                  product_codes,
                  exchange_rates,
                  branches,
                  products,
                  categories,
                  update=True)



if __name__ == "__main__":
    main()