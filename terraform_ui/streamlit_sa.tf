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
GITHUB_TOKEN=${var.github_token}
SCHEMA_REPO_OWNER=${var.schema_repo_owner}
SCHEMA_REPO_NAME=${var.schema_repo_name}
SCHEMA_REPO_PATH=${var.schema_repo_path}
SCHEMA_REPO_DEFAULT_BRANCH=${var.schema_repo_branch}
ALLOW_SAVE_TO_DEFAULT_BRANCH=${var.allow_save_to_default_branch}
EOT
  filename = "${path.module}/../streamlit_ev/.env"
}
