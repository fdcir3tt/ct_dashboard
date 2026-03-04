import os
import subprocess,warnings

warnings.filterwarnings('ignore')

from pathlib import Path
from dashboard.data_loader import load_invoices,load_product_codes,load_exchange_rates,load_branches,load_categories,load_products
from dashboard.preprocess import process_data

DATA_PATH = Path('data')

def main():
    
# -----------------------------------------------------------
# ACTUALIZAR DATOS
# -----------------------------------------------------------
    print("Revisando actualizaciones ...")

    if ( not os.path.exists(DATA_PATH/'raw'/'gadm41_MEX_shp') ):
        print(" ="*25)
        print("||   Comenzando extracción de archivos geográficos   ||")
        print(" ="*25)

        subprocess.run(["python", "scripts/shapefile_extraction.py"])
    
    
    print(" ="*25)
    print("||   Comenzando ingesta de datos históricos  ||")
    print(" ="*25)

    try:
        subprocess.run(["python", "scripts/ingest.py"])
    except Exception as e :
        print(f"No se pudo realizar ingesta de datos históricos :{e}")

    
    print(" ="*25)
    print("||   Comenzando actualización de conversiones de moneda  ||")
    print(" ="*25)
    try:
        subprocess.run(["python", "scripts/exchange_rates_update.py"])
    except Exception as e :
        print(f"No se pudo realizar actualización de conversiones USD a MXN :{e}")

    print("Proceso de actualización completo !!")

# -----------------------------------------------------------
# CARGAR DATOS
# -----------------------------------------------------------
    print(" Comenzando carga de datos...")
    invoices = load_invoices()

    product_codes =load_product_codes()
    exchange_rates = load_exchange_rates()

    branches = load_branches()
    categories = load_categories()
    products = load_products()

    print("Carga completa!!")
    process_data (invoices,
                  product_codes,
                  exchange_rates,
                  branches,
                  products,
                  categories,
                  update=True)
    print("Proceso de datos completo!!")


if __name__ == "__main__":
    main()