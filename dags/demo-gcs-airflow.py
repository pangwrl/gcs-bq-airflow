from airflow.models import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
import pandas as pd
import requests

API_URL = "https://bigdata.mwa.co.th/data-service/internal/big-data/api/v1/783f543c-666c-35b4-795b-40dd2446b291/7e911fa9-0a52-970a-eef5-2170851f3530/data?token=3XSOeKch6WiCXcw37EWhVX0Z0mPLncwmwTY6fgkm6tVCaIuNU11IiRRydPCUadnFGvfV2mPPrLc6hUk87JtA6rJSPVKNEr0HhJOuRPQ0CR3v3kaFIzk71Bm1N8uqST2b"

GCS_BUCKET_NAME = "asia-southeast1-water-qauli-51cdc2a6-bucket" 
GCS_OBJECT_NAME = "data/water_data.csv"
LOCAL_GCS_MOUNT_PATH = f"/home/airflow/gcs/{GCS_OBJECT_NAME}"


def fetch_api():
        
    response = requests.get(API_URL)

    if response.status_code == 200:
        json_data = response.json()
        records = json_data.get('data', [])
        return records
        
    else:
        raise Exception(f"Failed to fetch data: {response.status_code}")


def transform_data(ti, **kwargs):
    
    water_data = ti.xcom_pull(task_ids='fetch_api')

    if not water_data:
        print("No data received from fetch_api task.")
        return

    df = pd.json_normalize(water_data)
    df.to_csv(LOCAL_GCS_MOUNT_PATH, index=False)
    print(f"Output to {LOCAL_GCS_MOUNT_PATH}")


with DAG(
    "demo_gcs_airflow",
    start_date=days_ago(1),
    schedule_interval=None,
    catchup=False
) as dag:

    t1 = PythonOperator(
        task_id="fetch_api",
        python_callable=fetch_api

    )

    t2 = PythonOperator(
        task_id="transform_data",
        python_callable=transform_data
        
    )

    t3 = BashOperator(
        task_id= "bq_load",
        bash_command= "bq load \
        --source_format=CSV \
        --autodetect \
        dataset.water \
        gs://asia-southeast1-water-qauli-51cdc2a6-bucket/data/water_data.csv"
    )

    t1 >> t2 >> t3
