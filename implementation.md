# Chicago Crime Pipeline - Implementation Guide

This document provides step-by-step instructions to set up the Chicago Crime data pipeline from scratch.

## Prerequisites

- Git installed
- Docker and Docker Compose installed
- Google Cloud Platform (GCP) account with a project
- Terraform installed (optional, for infrastructure setup)

---

## Part 1: Clone the Repository

### Step 1.1: Clone the GitHub Repository

```bash
git clone https://github.com/code-hy/chicago_crime_pipeline.git
cd chicago_crime_pipeline
```

---

## Part 2: GCP Setup

### Step 2.1: Create a GCP Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click **Select a project** → **New Project**
3. Enter project name: `chicago-crime-pipeline` (or any name)
4. Note down your **Project ID** (e.g., `chicago-crime-123`)

### Step 2.2: Enable Required APIs

In GCP Console, enable the following APIs:
- **BigQuery API**
- **Cloud Storage API**
- **Compute Engine API** (for GCE default service account)

### Step 2.3: Create a Service Account

1. Go to **IAM & Admin** → **Service Accounts**
2. Click **+ CREATE SERVICE ACCOUNT**
3. Fill in:
   - Service account name: `airflow-sa`
   - Service account ID: `airflow-sa`
4. Grant roles:
   - **BigQuery Admin**
   - **Storage Object Admin**
   - **Storage Bucket Admin**
5. Click **DONE**

### Step 2.4: Create and Download Service Account Key

1. Click on the service account you just created
2. Go to **Keys** tab
3. Click **ADD KEY** → **Create new key**
4. Select **JSON** and click **CREATE**
5. Save the downloaded file as `gcp-key.json`

### Step 2.5: Move the Key File

```bash
mkdir -p credentials
mv /path/to/gcp-key.json credentials/
```

---

## Part 3: Infrastructure Setup (Optional - Using Terraform)

If you want to create GCS bucket and BigQuery dataset automatically:

### Step 3.1: Initialize Terraform

```bash
cd terraform
terraform init
```

### Step 3.2: Apply Terraform

```bash
terraform apply -var="project_id=YOUR_PROJECT_ID" -var="region=us-central1"
```

**Note:** Replace `YOUR_PROJECT_ID` with your actual GCP project ID.

This will create:
- GCS bucket: `{project-id}-crime-data-lake`
- BigQuery dataset: `chicago_crime_data`

---

## Part 4: Manual GCP Resources (Alternative)

If not using Terraform, create manually:

### Step 4.1: Create GCS Bucket

1. Go to Cloud Storage → **Create Bucket**
2. Name: `{YOUR_PROJECT_ID}-crime-data-lake`
3. Location: `US` or `us-central1`
4. Click **CREATE**

### Step 4.2: Create BigQuery Dataset

1. Go to BigQuery → **+ CREATE DATASET**
2. Dataset ID: `chicago_crime_data`
3. Location: `US`
4. Click **CREATE**

### Step 4.3: Create Staging Table

In BigQuery Query Editor, run:

```sql
CREATE TABLE IF NOT EXISTS `{YOUR_PROJECT_ID}.chicago_crime_data.staging_crimes`
(
  ID INT64,
  crime_date TIMESTAMP,
  year INT64,
  month INT64,
  crime_type STRING,
  location STRING,
  Arrest BOOL,
  Domestic BOOL
)
```

---

## Part 5: Update DAG Configuration

### Step 5.1: Update Project IDs in DAG

Edit `dags/crime_pipeline_dag.py` and replace placeholder project IDs:

```python
# Find and replace:
GCS_BUCKET = "YOUR_PROJECT_ID-crime-data-lake"
BQ_STAGING_TABLE = "YOUR_PROJECT_ID.chicago_crime_data.staging_crimes"
BQ_PROD_TABLE = "YOUR_PROJECT_ID.chicago_crime_data.prod_crimes"
```

Replace `YOUR_PROJECT_ID` with your actual GCP project ID.

---

## Part 6: Docker Environment Setup

### Step 6.1: Build Docker Image

```bash
docker-compose build
```

### Step 6.2: Start Airflow

```bash
docker-compose up -d
```

### Step 6.3: Wait for Services to Initialize

```bash
sleep 30
```

### Step 6.4: Restart Webserver (if needed)

```bash
docker-compose restart airflow-webserver
```

---

## Part 7: Configure Airflow Connections

### Step 7.1: Access Airflow UI

1. Open browser: http://localhost:8081
2. Login: `airflow` / `airflow`

### Step 7.2: Configure GCP Connection

1. Go to **Admin** → **Connections**
2. Click **+** to add new connection
3. Fill in:
   - **Conn Id**: `google_cloud_default`
   - **Conn Type**: `Google Cloud`
   - **Project ID**: Your GCP project ID
   - **Keyfile JSON**: Paste contents of `credentials/gcp-key.json`
4. Click **Save**

### Step 7.3: Configure Spark Connection (Optional)

If using Spark later:

1. Go to **Admin** → **Connections**
2. Click **+** to add new connection
3. Fill in:
   - **Conn Id**: `spark_default`
   - **Conn Type**: `Spark`
   - **Host**: `local[*]`
4. Click **Save**

---

## Part 8: Run the Pipeline

### Step 8.1: Trigger the DAG

1. In Airflow UI, find `chicago_crime_pipeline` DAG
2. Click the **Play** button to trigger

### Step 8.2: Monitor Execution

1. Click on the DAG name
2. Watch tasks progress:
   - `download_data` - Downloads CSV from Chicago portal
   - `upload_to_gcs` - Uploads to GCS
   - `process_to_bq` - Processes and loads to BigQuery staging
   - `transform_to_prod` - Creates partitioned production table

### Step 8.3: Check Logs

If any task fails:
1. Click on the failed task
2. Click **Log** to view error details

---

## Part 9: Verify Data in BigQuery

### Step 9.1: Query Staging Table

```sql
SELECT COUNT(*) as total_rows FROM `{YOUR_PROJECT_ID}.chicago_crime_data.staging_crimes`
```

### Step 9.2: Query Production Table

```sql
SELECT * FROM `{YOUR_PROJECT_ID}.chicago_crime_data.prod_crimes` LIMIT 10
```

---

## Part 10: Create Looker Studio Dashboard

### Step 10.1: Connect to BigQuery

1. Go to [Looker Studio](https://lookerstudio.google.com/)
2. Click **Create** → **Data Source**
3. Select **BigQuery**
4. Select your project → `chicago_crime_data` → `prod_crimes`
5. Click **Connect**

### Step 10.2: Create Dashboard

Add visualizations:
1. **Bar Chart**: crime_type dimension, Record Count metric
2. **Time Series**: crime_date dimension, Record Count metric

---

## Project Structure

```
chicago_crime_pipeline/
├── .gitignore              # Git ignore rules
├── Dockerfile               # Airflow Docker image
├── docker-compose.yml       # Docker compose for Airflow
├── README.md               # Project overview
├── credentials/             # GCP credentials (NOT pushed to git)
│   └── gcp-key.json
├── dags/
│   ├── crime_pipeline_dag.py    # Main Airflow DAG
│   └── spark_jobs/
│       └── process_crime_data.py  # Spark job (if needed)
├── logs/                   # Airflow logs (NOT pushed to git)
└── terraform/               # Terraform IaC
    ├── main.tf
    └── variables.tf
```

---

## Troubleshooting

### Issue: DAG Import Errors
- Check scheduler logs: `docker logs chicago_crime_pipeline-airflow-scheduler-1`

### Issue: Connection Errors
- Verify GCP credentials in Airflow UI → Admin → Connections

### Issue: BigQuery Table Not Found
- Create staging table manually in BigQuery console

### Issue: Download Timeout
- Check network connection
- Reduce date range in download function

---

## Clean Up

### Stop Docker Containers
```bash
docker-compose down
```

### Destroy GCP Resources (Optional)
```bash
cd terraform
terraform destroy -var="project_id=YOUR_PROJECT_ID"
```

---

## Summary of Commands

```bash
# Clone repo
git clone https://github.com/code-hy/chicago_crime_pipeline.git
cd chicago_crime_pipeline

# Setup GCP credentials
mkdir -p credentials
mv gcp-key.json credentials/

# Update DAG with project ID
# Edit: dags/crime_pipeline_dag.py

# Build and start
docker-compose build
docker-compose up -d

# Access Airflow
# URL: http://localhost:8081
# User: airflow
# Pass: airflow
```

---

**Note:** Never commit secrets, credentials, or API keys to version control. The `.gitignore` file is configured to exclude the `credentials/` directory.