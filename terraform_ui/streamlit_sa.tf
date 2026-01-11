resource "google_service_account" "streamlit_worker" {
  account_id   = "streamlit-worker"
  display_name = "Streamlit Worker Service Account"
  project      = var.project_id
}

resource "google_storage_bucket_iam_member" "streamlit_storage_admin" {
  bucket = var.schemas_bucket
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.streamlit_worker.email}"
}

resource "google_bigquery_dataset_iam_member" "streamlit_bq_viewer" {
  project    = var.project_id
  dataset_id = var.bq_dataset
  role       = "roles/bigquery.dataViewer"
  member     = "serviceAccount:${google_service_account.streamlit_worker.email}"
}

resource "google_project_iam_member" "streamlit_bq_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.streamlit_worker.email}"
}

resource "local_file" "streamlit_env" {
  content  = <<EOT
BUCKET_NAME=${var.schemas_bucket}
GCP_PROJECT=${var.project_id}
REPO_JSON_FILE=repo.json
BQ_DATASET=${var.bq_dataset}
BQ_TABLE=${var.bq_table}
EOT
  filename = "${path.module}/../streamlit_ev/.env"
}
