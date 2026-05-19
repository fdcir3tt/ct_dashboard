import json
import pandas as pd

from pathlib import Path
from typing import Any
from common.registry import FUNCTION_REGISTRY

from airflow.operators.python import PythonOperator
from airflow.utils.trigger_rule import TriggerRule
from airflow.exceptions import AirflowSkipException,AirflowFailException

class ETL_pipeline():
    def __init__(self,extract_fns:list[str],transform_fns:list[str],load_fns:list[str],conn_str:str,save_dict:dict[str,str],conditions_dict:dict[str,dict[str,str]]):
        self.extract_fns = extract_fns
        self.transform_fns = transform_fns
        self.load_fns = load_fns
        self.conn_str = conn_str
        self.save_dict = save_dict
        self.delete_dict = {}
        self.task_conditions_dict = conditions_dict

    def make_gather_paths_task(self,task_title:str)->PythonOperator:

        gather_paths_task = PythonOperator(
            task_id=task_title,
            python_callable= gather_paths,
            trigger_rule=TriggerRule.ALL_DONE
        )
        self.delete_dict[task_title] = "path_strings"
        return gather_paths_task
    
    def make_extraction_tasks(self)->list[PythonOperator]:
        extract_tasks =[]
        for function_name in self.extract_fns :
            task = PythonOperator(
                task_id=function_name,
                op_args =[function_name,self.conn_str],
                op_kwargs = self.task_conditions_dict,
                python_callable=extract,
            )

            extract_tasks.append(task)
        return extract_tasks
    
    def make_transform_tasks(self)->list[PythonOperator]:
        transform_tasks =[]
        for function_name in self.transform_fns :
            task = PythonOperator(
                task_id=function_name,
                op_args =[function_name,self.save_dict],
                op_kwargs = self.task_conditions_dict,
                python_callable=transform,
            )

            transform_tasks.append(task)
        return transform_tasks

    def make_load_tasks(self)->list[PythonOperator]:
        load_tasks =[]
        for function_name in self.load_fns :
            task = PythonOperator(
                task_id=function_name,
                op_args =[function_name,self.conn_str],
                op_kwargs = self.task_conditions_dict,
                python_callable=load,
            )

            load_tasks.append(task)
        return load_tasks

    def make_delete_tmp_files_task(self)->None:
        delete_tmp_files_task = PythonOperator(
            task_id="delete_tmp_files",
            op_args = [self.delete_dict],
            python_callable= delete_temp_files,
            trigger_rule=TriggerRule.ALL_DONE
        )
        return delete_tmp_files_task
        

def generate_tmp_path_strings(data_dict:dict[str,pd.DataFrame|list[dict[str,Any]]])->list[str]:
    path_strings = []
    for file_name,data in data_dict.items():
        if isinstance(data,pd.DataFrame):
            suffix=".parquet"
        if isinstance(data,list):
            suffix=".json"
        path_str = f"/tmp/{file_name}{suffix}"
        path_strings.append(path_str)
    return path_strings

def save_data(data:list[dict[str,Any]]|pd.DataFrame|dict[str,Any],path_strings:str|list[str])->None:
    # Un archivo
    if isinstance(path_strings,str):
        file_path = Path(path_strings)
        if isinstance(data,list):
            save_records(data,file_path)
        if isinstance(data,pd.DataFrame):
            data.to_parquet(file_path,engine="pyarrow")
    # Varios archivos
    if isinstance(path_strings,list):
        for path_str in path_strings:
            file_path = Path(path_str)
            file_name = str(file_path.stem)
            print(f"Guardando {file_name} ... ")
            if file_path.suffix==".json":
                save_records(data[file_name],file_path)
            
            if file_path.suffix==".parquet":
                data[file_name].to_parquet(file_path,engine="pyarrow")
        

def load_data(path_strings:str|list[str])->list[dict[str,Any]]|pd.DataFrame|dict[str,Any]:
    # Un archivo
    if isinstance(path_strings,str):
        file_path = Path(path_strings)
        if file_path.suffix == ".json":
                data = load_records(file_path)
        if file_path.suffix == ".parquet":
                data = pd.read_parquet(file_path,engine="pyarrow")
        return data
    # Varios archivos
    data = {}
    for path_str in path_strings:
            file_path = Path(path_str)
            file_name = str(file_path.stem)
            if file_path.suffix == ".json":
                data[file_name] = load_records(file_path)
            if file_path.suffix == ".parquet":
                data[file_name] = pd.read_parquet(file_path,engine="pyarrow")
    return data 

def save_records(records:list[dict[str,Any]],file_path:Path)->None:
    with open(file_path, "w") as f:
        json.dump(records, f)

def load_records(file_path:Path)->list[dict[str,Any]]:
    with open(file_path) as f:
        records = json.load(f)
    return records

def delete_files(file_paths:str|list[str]|Path|list[Path])->None:
    if isinstance(file_paths, Path):
        file_paths.unlink()
        print(f"Archivo '{file_paths}' borrado correctamente!")
        return None
    
    if isinstance(file_paths, str):
        file_path = Path(file_paths)
        file_path.unlink()
        print(f"Archivo '{file_paths}' borrado correctamente!")
        return None
    
    for path in file_paths:
        if isinstance(path, str):
            file_path = Path(path)
            file_path.unlink()
            print(f"Archivo '{path}' borrado correctamente!") 
            continue
        path.unlink()
        print(f"Archivo '{path}' borrado correctamente!")        

def data_is_empty(data:pd.DataFrame|list[dict[str,Any]])->bool:
    if isinstance(data,pd.DataFrame):
        return data.empty
    elif isinstance(data,list):
        return len(data)==0

def extract(extract_fn_name:str,conn_str=None,**context):
    extract_fn = FUNCTION_REGISTRY[extract_fn_name]
    extracted_data = extract_fn(conn_str=conn_str,**context)
    file_name = extract_fn_name.split("extract_")[1]
    path_string = generate_tmp_path_strings({file_name:extracted_data})[0]
    
    is_empty =  data_is_empty(extracted_data) #len(extracted_data)==0
    if is_empty:
        if context["extracted_data_is_empty"][file_name]=="skip":
            raise AirflowSkipException(f"Skipping task,failed to extract:'{file_name}' ")
        if context["extracted_data_is_empty"][file_name]=="stop":
            raise AirflowFailException(f"Task failed,failed to extract:'{file_name}'")
        
    save_data(extracted_data,path_string)
    key = "path_string"
    context["ti"].xcom_push(key=key, value=path_string)


def transform(transform_fn_name:str,save_dict:dict[str,str],**context):
    extracted_path_strings = context["ti"].xcom_pull(task_ids="gather_extracted_paths", key="path_strings")
    extracted_data = load_data(extracted_path_strings)
    
    
    extracted_data_name = transform_fn_name.split("transform_")[1]
    
    not_extracted = extracted_data_name not in extracted_data.keys()
    if not_extracted:
        if context["extracted_data_is_empty"][extracted_data_name]=="skip":
            raise AirflowSkipException(f"Skipping task,no data to transform:'{extracted_data_name}'")
        if context["extracted_data_is_empty"][extracted_data_name]=="stop":
            raise AirflowFailException(f"Task failed,no data to transform:'{extracted_data_name}' ")
        
    transform_fn = FUNCTION_REGISTRY[transform_fn_name]    
    transformed_data = transform_fn(extracted_data)
    
    path_string = generate_tmp_path_strings({save_dict[extracted_data_name]:transformed_data})[0]
    
    save_data(transformed_data,path_string)
    
    context["ti"].xcom_push(key="path_string",value=path_string)

def load(load_fn_name:str,conn_str:str,**context):
    
    extracted_path_strings = context["ti"].xcom_pull(task_ids="gather_transformed_paths", key="path_strings")
    transformed_data = load_data(extracted_path_strings)
    
    transformed_data_name = load_fn_name.split("load_")[1]
    not_transformed = transformed_data_name not in transformed_data.keys()
    if not_transformed:
            if context["transformed_data_is_empty"][transformed_data_name]=="skip":
                raise AirflowSkipException(f"Skipping task,no data to load:'{transformed_data_name}'")
            if context["transformed_data_is_empty"][transformed_data_name]=="stop":
                raise AirflowFailException(f"Task failed,no data to load:'{transformed_data_name}' ")
    load_fn = FUNCTION_REGISTRY[load_fn_name]
    load_fn(conn_str,transformed_data)

def delete_temp_files(delete_dict:dict[str,str],**context):
    temp_files_path_strings =[]
    for task_id,key in delete_dict.items():
        path_strings = context["ti"].xcom_pull(task_ids=task_id, key=key)
        temp_files_path_strings += path_strings
    
    delete_files(temp_files_path_strings)
    
def gather_paths(**context):
    upstream_task_ids = context["ti"].task.upstream_task_ids
    gathered_paths = []

    for task_id in upstream_task_ids:
        value = context["ti"].xcom_pull(task_ids=task_id,key="path_string")
        if value is None:
            continue
        gathered_paths.append(value)
    context["ti"].xcom_push(key="path_strings",  value=gathered_paths)

