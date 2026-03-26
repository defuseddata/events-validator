resource "archive_file" "function_zip" {
  type        = "zip"
  source_dir  = "${path.module}/${var.function_source_dir}"
  output_path = "code.zip"
}
# 1. Create a dedicated Service Account for the Function
resource "google_service_account" "function_sa" {
  account_id   = "ev-validator-sa"
  display_name = "Event Validator Cloud Function SA"
}

# 2. Grant Bucket Reader permissions
resource "google_storage_bucket_iam_member" "bucket_reader" {
  bucket = google_storage_bucket.eventvalidator_schemas_bucket.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.function_sa.email}"
}

# 3. Grant BigQuery Data Editor permissions for logging
resource "google_bigquery_dataset_iam_member" "bq_editor" {
  dataset_id = google_bigquery_dataset.event_validator_dataset.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.function_sa.email}"
}

resource "google_cloudfunctions2_function" "function" {
  name = "eventvalidatorfunction"
  location = var.region
  description = "event validator function"

  build_config {
    runtime = "nodejs20"
    entry_point = "validateEvent"

    source {
      storage_source {
        bucket = google_storage_bucket.eventvalidatorfunction_bucket.name
        object = google_storage_bucket_object.eventvalidatorfunction_object.name
      }
    }
  }

  service_config {
    min_instance_count  = var.backend_min_instances
    max_instance_count  = var.backend_max_instances
    available_memory    = "512M"
    timeout_seconds     = 60
    ingress_settings = "ALLOW_ALL"
    all_traffic_on_latest_revision = true
    service_account_email = google_service_account.function_sa.email
    environment_variables = {
      BQ_DATASET = google_bigquery_table.event_validator_data_table.dataset_id
      BQ_TABLE = google_bigquery_table.event_validator_data_table.table_id
      SCHEMA_BUCKET = google_storage_bucket.eventvalidator_schemas_bucket.name
      EVENT_NAME_ATTRIBUTE = var.EVENT_NAME_ATTRIBUTE
      EVENT_DATA_PATH = var.EVENT_DATA_PATH
      LOG_VALID_FIELDS = var.LOG_VALID_FIELDS_FLAG
      LOG_PAYLOAD_WHEN_ERROR = var.LOG_PAYLOAD_WHEN_ERROR_FLAG
      LOG_PAYLOAD_WHEN_VALID = var.LOG_PAYLOAD_WHEN_VALID_FLAG
    }
  }
}
