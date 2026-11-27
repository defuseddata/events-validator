# The GitHub token lives in Secret Manager; Cloud Run only holds a reference to it,
# so reading the service configuration (console, `gcloud run services describe`)
# does not reveal the value. The app still reads the GITHUB_TOKEN environment variable.
#
# The secret is created only when GitOps is enabled (github_token is not empty).
# `nonsensitive` is applied to the boolean only: count cannot depend on a sensitive value.
locals {
  github_token_enabled = nonsensitive(var.github_token != "")
}

resource "google_secret_manager_secret" "github_token" {
  count     = local.github_token_enabled ? 1 : 0
  project   = var.project_id
  secret_id = "event-validator-github-token"

  replication {
    auto {}
  }

  depends_on = [google_project_service.required_services]
}

# Rotation: change github_token in terraform.tfvars and run `terraform apply`.
# A new version is created and Cloud Run is pointed at it (a new revision), which is why the
# service pins the version instead of using "latest". create_before_destroy keeps the old
# version alive until the service has moved to the new one.
resource "google_secret_manager_secret_version" "github_token" {
  count       = local.github_token_enabled ? 1 : 0
  secret      = google_secret_manager_secret.github_token[0].id
  secret_data = var.github_token

  lifecycle {
    create_before_destroy = true
  }
}

# Only the UI's service account may read the value, and only this one secret.
resource "google_secret_manager_secret_iam_member" "streamlit_github_token_accessor" {
  count     = local.github_token_enabled ? 1 : 0
  project   = var.project_id
  secret_id = google_secret_manager_secret.github_token[0].secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.streamlit_worker.email}"
}
