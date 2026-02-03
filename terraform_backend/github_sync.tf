resource "github_repository_file" "schemas" {
  for_each            = fileset("${path.module}/src/GA4 Recommended/schemas", "*.json")
  repository          = var.schema_repo_name
  branch              = "main"
  file                = "schemas/${each.key}"
  content             = file("${path.module}/src/GA4 Recommended/schemas/${each.key}")
  commit_message      = "Add schema ${each.key} via Terraform"
  commit_author       = "Terraform"
  commit_email        = "terraform@example.com"
  overwrite_on_create = true

  lifecycle {
    ignore_changes = [
      content,
      commit_message,
      commit_author,
      commit_email,
    ]
  }
}

resource "github_repository_file" "repo_json" {
  repository          = var.schema_repo_name
  branch              = "main"
  file                = "schemas/repo.json"
  content             = file("${path.module}/src/GA4 Recommended/repo.json")
  commit_message      = "Add repo.json via Terraform"
  commit_author       = "Terraform"
  commit_email        = "terraform@example.com"
  overwrite_on_create = true

  lifecycle {
    ignore_changes = [
      content,
      commit_message,
      commit_author,
      commit_email,
    ]
  }
}



# --- Service Account for GitHub Actions ---
resource "google_service_account" "github_actions" {
  account_id   = "github-actions-uploader"
  display_name = "GitHub Actions GCS Uploader"
}

resource "google_storage_bucket_iam_member" "github_actions_writer" {
  bucket = google_storage_bucket.eventvalidator_schemas_bucket.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.github_actions.email}"
}

# --- Workload Identity Federation ---

resource "google_iam_workload_identity_pool" "github_pool" {
  workload_identity_pool_id = "github-actions-pool-v3"
  display_name              = "GitHub Actions Pool"
  description               = "Identity pool for GitHub Actions"
}

resource "google_iam_workload_identity_pool_provider" "github_provider" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github_pool.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-provider"
  display_name                       = "GitHub Provider"
  description                        = "OIDC Provider for GitHub Actions"
  
  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.actor"      = "assertion.actor"
    "attribute.repository" = "assertion.repository"
  }

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

# Grant the GitHub Actions identity access to impersonate the Service Account
# ONLY requests coming from the specific GitHub repository will be allowed.
resource "google_service_account_iam_member" "workload_identity_user" {
  service_account_id = google_service_account.github_actions.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github_pool.name}/attribute.repository/${var.schema_repo_owner}/${var.schema_repo_name}"
}

# --- GitHub Secrets ---

# We no longer need the private key. Instead, we provide the WIF configuration.

resource "github_actions_secret" "gcp_workload_identity_provider" {
  repository      = var.schema_repo_name
  secret_name     = "GCP_WORKLOAD_IDENTITY_PROVIDER"
  plaintext_value = google_iam_workload_identity_pool_provider.github_provider.name
}

resource "github_actions_secret" "gcp_service_account" {
  repository      = var.schema_repo_name
  secret_name     = "GCP_SERVICE_ACCOUNT"
  plaintext_value = google_service_account.github_actions.email
}

resource "github_actions_secret" "gcs_bucket_name" {
  repository      = var.schema_repo_name
  secret_name     = "GCS_BUCKET_NAME"
  plaintext_value = google_storage_bucket.eventvalidator_schemas_bucket.name
}
