
resource "google_service_account" "streamlit_worker" {
  account_id   = "streamlit-worker"
  display_name = "Streamlit Worker Service Account"
  project      = var.project_id
}

resource "google_storage_bucket_iam_member" "streamlit_storage_admin" {
  bucket = google_storage_bucket.eventvalidator_schemas_bucket.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.streamlit_worker.email}"
}

resource "google_service_account_key" "streamlit_worker_key" {
  service_account_id = google_service_account.streamlit_worker.name
}

resource "local_file" "streamlit_credentials" {
  content  = base64decode(google_service_account_key.streamlit_worker_key.private_key)
  filename = "${path.module}/../streamlit_ev/credentials.json"
}

resource "local_file" "streamlit_env" {
  content  = <<EOT
GOOGLE_APPLICATION_CREDENTIALS=credentials.json
BUCKET_NAME=${google_storage_bucket.eventvalidator_schemas_bucket.name}
GCP_PROJECT=${var.project_id}
REPO_JSON_FILE=repo.json
EOT
  filename = "${path.module}/../streamlit_ev/.env"
}
