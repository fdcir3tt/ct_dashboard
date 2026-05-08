import os 
import pandas as pd
import great_expectations as gx 
import datetime
import numpy as np

from typing import Any
from concurrent.futures import ProcessPoolExecutor, as_completed
from mlops.utils import data_dir ,Date,identify_outlier_sales,save_file_safe

# Configuración
BRANCH = "HERMOSILLO, SON."
TODAY = pd.to_datetime(Date.today())
START_DATE = pd.to_datetime(TODAY - datetime.timedelta(days=365*2))
DIR_PATH = data_dir/"processed"/BRANCH


context = gx.get_context()
data_source_name = "local_processed" 
data_source = context.data_sources.add_pandas(name=data_source_name)

data_asset_name = "ventas_producto"
data_asset = data_source.add_dataframe_asset(name=data_asset_name)

batch_definition_name = "ventas_diarias"
batch_definition = data_asset.add_batch_definition_whole_dataframe(
    batch_definition_name
)

def load_dataset(dataset_name:str)->pd.DataFrame:
    branch,productId = dataset_name.split('_')
    dir_path = data_dir/"processed"/branch
    path = dir_path/f"{productId}.parquet"
    dataset = pd.read_parquet(path)
    return dataset

def validate_column_expectations(dataset:pd.DataFrame,dataset_name:str)->bool:
    batch_parameters = {"dataframe": dataset}
    batch = batch_definition.get_batch(batch_parameters=batch_parameters)

    suite_name = f"{data_source_name}.{dataset_name}.validation.dev"
    suite = gx.ExpectationSuite(name=suite_name)
    suite = context.suites.add(suite)

    productId_exists_expectation = gx.expectations.ExpectColumnToExist(column="productId")
    quantity_column_exists_expectation = gx.expectations.ExpectColumnToExist(column="quantity")
    date_column_exists_expectation = gx.expectations.ExpectColumnToExist(column="date")
    cost_exists_expectation = gx.expectations.ExpectColumnToExist(column="cost")
    branch_exists_expectation = gx.expectations.ExpectColumnToExist(column="branch")
    month_exists_expectation = gx.expectations.ExpectColumnToExist(column="month")
    year_exists_expectation = gx.expectations.ExpectColumnToExist(column="year")

    suite.add_expectation(productId_exists_expectation)
    suite.add_expectation(quantity_column_exists_expectation)
    suite.add_expectation(date_column_exists_expectation)
    suite.add_expectation(cost_exists_expectation)
    suite.add_expectation(branch_exists_expectation)
    suite.add_expectation(month_exists_expectation)
    suite.add_expectation(year_exists_expectation)

    pipeline_stage = "profiling"
    validation_definition_name = f"{dataset_name}.{pipeline_stage}.{suite_name}.dev"
    validation_definition = gx.ValidationDefinition(
        data=batch_definition, suite=suite, name=validation_definition_name
    )
    validation_definition = context.validation_definitions.add(validation_definition)
    validation_results = validation_definition.run(batch_parameters=batch_parameters)

    #print(f"Dataset {dataset_name} validado: {validation_results.success}")
    return validation_results.success

def profile_dataset(dataset_name:str)->dict[str,Any]:
    # Carga
    dataset = load_dataset(dataset_name)

    mask =( (dataset["date"] >=START_DATE) 
        & (dataset["date"] <= TODAY) )
    dataset = dataset[mask]

    # Validación de columnas

    if validate_column_expectations(dataset,dataset_name):
        columns = ["productId","quantity","date","clientId","cost","branch","month","year"]
    
        df = dataset.copy()
        df = df[columns]
        df = identify_outlier_sales(df,"productId")
        productId = df["productId"].iloc[0]

        row = { "productId":df["productId"].iloc[0] ,
                "total_sales" : len(df),
                "total_units_sold" : df["quantity"].sum(),
                "sales_range":f"[ {df["quantity"].min()}-{df["quantity"].max()} ]",
                "oldest_date" : df["date"].min(),
                "latest_sales_date" : df["date"].max(),
                "month_avg_sales" : df.groupby(["month","year"])["quantity"].sum().mean(),
                "number_of_outliers" : df["is_outlier"].sum(),
                "avg_sales_gap" : df["date"].diff().dropna().mean(),
                "path" : str(DIR_PATH / f"{productId}.parquet"),
                "branch" : df["branch"].iloc[0] ,
                "avg_cost" : df["cost"].mean(),
                "profile_date" : TODAY }
    else:
        row={   "productId":dataset_name.split('_')[1] ,
                "total_sales" : len(dataset),
                "total_units_sold" : np.nan ,
                "sales_range":f"[ ? ]",
                "oldest_date" : np.nan,
                "latest_sales_date" : np.nan,
                "month_avg_sales" : np.nan,
                "number_of_outliers" : np.nan,
                "avg_sales_gap" : np.nan,
                "path" : str(DIR_PATH/ f"{productId}.parquet"),
                "branch" : dataset_name.split('_')[0] ,
                "avg_cost" : np.nan,
                "profile_date" : TODAY }
    
    return row

def main(datasets:list[str])->pd.DataFrame:
    
    data =[]
    with ProcessPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(profile_dataset, dataset_name) for dataset_name in datasets]
        counter = 0
        total_datasets = len(datasets)
        for f in as_completed(futures):
            row = f.result()
            data.append(row)
            # Actualización  
            print(f"Datos perfilados: {counter} / {total_datasets}",end='\r')
            counter +=1

    profile_df = pd.DataFrame(data)

    return profile_df




if __name__ == "__main__":

    # Carga de dataset 
    
    branch_products = [ p.split('.')[0] for p in os.listdir(DIR_PATH)]
    datasets = [f"{BRANCH}_{productId}" for productId in branch_products]
    profile_df = main(datasets)

    profile_path = data_dir / "raw" / "dataset_profiles.parquet"
    save_file_safe(profile_df,profile_path)