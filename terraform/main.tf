terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 4.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_storage_bucket" "crime_data_lake" {
  name          = "${var.project_id}-crime-data-lake"
  location      = var.region
  force_destroy = true

  uniform_bucket_level_access = true

  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type = "Delete"
    }
  }
}

resource "google_bigquery_dataset" "crime_dataset" {
  dataset_id  = "chicago_crime_data"
  project     = var.project_id
  location    = var.region
  description = "Dataset containing Chicago Crime statistics"
}
