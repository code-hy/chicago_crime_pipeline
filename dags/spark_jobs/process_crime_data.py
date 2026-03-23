import sys
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, to_timestamp, year, month

gcs_input_path = sys.argv[1]
bq_table = sys.argv[2]
temp_gcs_bucket = sys.argv[3]

spark = SparkSession.builder.appName("ChicagoCrimeProcessing").getOrCreate()

df = spark.read.option("header", "true").csv(gcs_input_path)

df_clean = (
    df.withColumn("date_ts", to_timestamp(col("Date"), "MM/dd/yyyy hh:mm:ss a"))
    .withColumn("year", year(col("date_ts")))
    .withColumn("month", month(col("date_ts")))
    .filter(col("Primary Type").isNotNull())
    .select(
        col("ID"),
        col("date_ts").alias("crime_date"),
        col("year"),
        col("month"),
        col("Primary Type").alias("crime_type"),
        col("Location Description").alias("location"),
        col("Arrest"),
        col("Domestic"),
    )
)

df_clean.write.format("bigquery").option("table", bq_table).option(
    "temporaryGcsBucket", temp_gcs_bucket
).mode("append").save()
