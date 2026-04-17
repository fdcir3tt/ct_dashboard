import pandas as pd
import argparse 

from mlops.utils import data_dir


DATA_PATH = data_dir / 'raw' / 'facturas_ventas.parquet'
parser = argparse.ArgumentParser("Script que extrae los mejores/peores productos de la sucursal especificada.")
parser.add_argument("--branch", type=str, help="Sucursal",default="HERMOSILLO, SON.")
parser.add_argument("--best", type=bool, help="Mejores/peores productos",default=True)
parser.add_argument("--n", type=int, help="Cantidad de productos",default=10)

args = parser.parse_args()


data = pd.read_parquet(DATA_PATH)

mask = (  ( data['branch']==args.branch) 
        & (~data['productId'].str.contains('CARGO'))
        & (~data["productId"].str.contains('SOF'))
        & (~data["productId"].str.contains('ESDMSF'))
        & (~data["productId"].str.contains('ESDKPK'))
        & (~data["productId"].str.contains('SERVICIO'))
        & (~data["productId"].str.contains('GARANTÍA'))
        ) 

df = data[mask]




top_products= (
            df
            .groupby("productId")["quantity"]
            .sum()
            .sort_values(ascending=(not args.best))
        )

print(top_products.head(args.n))
print(top_products.head(args.n).index)




