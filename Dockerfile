FROM apache/airflow:2.7.0

USER root
RUN apt-get update && apt-get install -y openjdk-17-jre-headless && rm -rf /var/lib/apt/lists/*
USER airflow

RUN pip install --no-cache-dir \
    apache-airflow-providers-google==10.6.0 \
    apache-airflow-providers-apache-spark==4.1.0 \
    apache-airflow-providers-celery==3.3.2 \
    pyspark==3.5.0 \
    gcsfs==2024.2.0 \
    pandas==2.0.3 \
    psycopg2-binary==2.9.7
