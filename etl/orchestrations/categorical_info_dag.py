from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.utils.trigger_rule import TriggerRule

from datetime import datetime, timedelta


from pipelines.categorical_info.extract import run_extract,gather_extracted_paths, \
                                               extract_product_category_rows,\
                                               extract_product_catalogue_rows,extract_product_codes_data,\
                                               extract_client_data,\
                                               extract_branch_docs

from pipelines.categorical_info.transform import run_transform,gather_transformed_paths,\
                                                 transform_product_codes,\
                                                 transform_product_category_rows,\
                                                 transform_client_data,\
                                                 transform_branch_docs

from pipelines.categorical_info.load import run_load,delete_temp_files,\
                                            load_categories_df,\
                                            load_clients_df,\
                                            load_product_codes_df,\
                                            load_branches_df

conn_str = "dashboard_app_db"
# Extract functions:
extract_fns = [extract_product_category_rows,\
               extract_product_catalogue_rows,extract_product_codes_data,\
               extract_client_data,\
               extract_branch_docs ]

# Transform functions:
transform_fns = [transform_product_codes,\
                 transform_product_category_rows,\
                 transform_client_data,\
                 transform_branch_docs]

# Load functions:
load_fns = [load_categories_df,\
            load_clients_df,\
            load_product_codes_df,\
            load_branches_df]



#  Configuración del DAG
default_args = {
    "owner": "Federico",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}

with DAG(
    dag_id="categorical_info",
    default_args=default_args,
    description="Pipeline información categórica ",
    schedule_interval="0 13 1 */2 *",  # Bimensual a las 6am
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["raw"],
) as dag:
    
    extract_tasks =[]
    for function in extract_fns :
       task = PythonOperator(
        task_id=function.__name__,
        op_args =[function],
        python_callable=run_extract,
    )

       extract_tasks.append(task)
       
    gather_extracted_paths_task = PythonOperator(
        task_id="gather_extracted_paths",
        python_callable= gather_extracted_paths,
        trigger_rule=TriggerRule.ALL_DONE
    )
    

    transform_tasks =[]
    for function in transform_fns :
       task = PythonOperator(
        task_id=function.__name__,
        op_args =[function],
        python_callable=run_transform,
    )

       transform_tasks.append(task)

    gather_transformed_paths_task = PythonOperator(
        task_id="gather_transformed_paths",
        python_callable= gather_transformed_paths,
        trigger_rule=TriggerRule.ALL_DONE
    )
    hook = PostgresHook(postgres_conn_id=conn_str)
    load_tasks =[]
    for function in load_fns :
       task = PythonOperator(
        task_id=function.__name__,
        op_args =[hook,function],
        python_callable=run_load,
    )

       load_tasks.append(task)

    delete_tmp_files =PythonOperator(
        task_id="delete_temp_files",
        python_callable=delete_temp_files,
        trigger_rule=TriggerRule.ALL_DONE
    )
    
    extract_tasks >> gather_extracted_paths_task >> transform_tasks >> gather_transformed_paths_task >> load_tasks >> delete_tmp_files