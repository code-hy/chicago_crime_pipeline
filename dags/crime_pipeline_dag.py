from datetime import datetime, timedelta
import requests
from airflow import DAG
from airflow.providers.google.cloud.operators.bigquery import (
    BigQueryExecuteQueryOperator,
)
from airflow.providers.google.cloud.transfers.local_to_gcs import (
    LocalFilesystemToGCSOperator,
)
from airflow.operators.python import PythonOperator
from airflow.exceptions import AirflowException

DATA_URL = "https://data.cityofchicago.org/resource/ijzp-q8t2.csv"

GCS_BUCKET = "project-b60ec3fb-d46b-4909-ae8-crime-data-lake"
BQ_STAGING_TABLE = "project-b60ec3fb-d46b-4909-ae8.chicago_crime_data.staging_crimes"
BQ_PROD_TABLE = "project-b60ec3fb-d46b-4909-ae8.chicago_crime_data.prod_crimes"

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": datetime(2023, 1, 1),
    "retries": 3,
    "retry_delay": 300,
}


def download_file_local(**kwargs):
    import time
    from datetime import datetime, timedelta

    local_path = "/tmp/crime_data.csv"
    max_retries = 3
    retry_count = 0

    ten_years_ago = datetime.now() - timedelta(days=365 * 3)
    date_filter = ten_years_ago.strftime("%Y-%m-%d")

    while retry_count < max_retries:
        try:
            session = requests.Session()
            session.headers.update(
                {"Accept": "application/csv", "User-Agent": "Mozilla/5.0"}
            )

            url = f"https://data.cityofchicago.org/resource/ijzp-q8t2.csv?$where=date%3E%3D'{date_filter}'&$limit=200000&$order=date ASC"
            response = session.get(url, stream=True, timeout=600)
            response.raise_for_status()

            with open(local_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            return local_path
        except Exception as e:
            retry_count += 1
            if retry_count >= max_retries:
                raise AirflowException(
                    f"Download failed after {max_retries} retries: {str(e)}"
                )
            time.sleep(60)


def process_to_bigquery(**kwargs):
    from google.cloud import bigquery
    import pandas as pd
    from datetime import datetime

    local_path = "/tmp/crime_data.csv"

    df = pd.read_csv(local_path, low_memory=False)

    df["crime_date"] = pd.to_datetime(df["date"], errors="coerce")
    df["year"] = df["crime_date"].dt.year
    df["month"] = df["crime_date"].dt.month

    df_clean = df[df["primary_type"].notna()].copy()

    df_final = df_clean[
        [
            "id",
            "crime_date",
            "year",
            "month",
            "primary_type",
            "location_description",
            "arrest",
            "domestic",
        ]
    ].copy()

    df_final = df_final.rename(
        columns={
            "id": "ID",
            "primary_type": "crime_type",
            "location_description": "location",
            "arrest": "Arrest",
            "domestic": "Domestic",
        }
    )

    client = bigquery.Client()

    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
    )

    load_job = client.load_table_from_dataframe(
        df_final, BQ_STAGING_TABLE, job_config=job_config
    )

    load_job.result()
    print(f"Loaded {len(df_final)} rows to {BQ_STAGING_TABLE}")


with DAG(
    "chicago_crime_pipeline",
    default_args=default_args,
    schedule_interval="@daily",
    catchup=False,
) as dag:
    t_download = PythonOperator(
        task_id="download_data", python_callable=download_file_local
    )

    t_upload = LocalFilesystemToGCSOperator(
        task_id="upload_to_gcs",
        src="/tmp/crime_data.csv",
        dst="raw/crime_data.csv",
        bucket=GCS_BUCKET,
        gcp_conn_id="google_cloud_default",
    )

    t_process = PythonOperator(
        task_id="process_to_bq",
        python_callable=process_to_bigquery,
    )

    sql_transform = f"""
    CREATE OR REPLACE TABLE `{BQ_PROD_TABLE}`
    PARTITION BY DATE(crime_date)
    CLUSTER BY crime_type
    AS
    SELECT * FROM `{BQ_STAGING_TABLE}`
    """

    t_bq_transform = BigQueryExecuteQueryOperator(
        task_id="transform_to_prod",
        sql=sql_transform,
        use_legacy_sql=False,
        location="us-central1",
    )

    t_download >> t_upload >> t_process >> t_bq_transform
