resource "github_repository_file" "schemas" {
  for_each            = var.schema_repo_name != "" ? fileset("${path.module}/src/GA4 Recommended/schemas", "*.json") : toset([])
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
  count               = var.schema_repo_name != "" ? 1 : 0
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


# --- GitHub Workflow Deployment ---
resource "github_repository_file" "workflow_file" {
  count               = var.schema_repo_name != "" ? 1 : 0
  repository          = var.schema_repo_name
  branch              = "main"
  file                = ".github/workflows/sync-to-gcs.yml"
  content             = file("${path.module}/templates/sync-to-gcs.yml")
  commit_message      = "Add GCS Sync Workflow (GCP Workload Identity) via Terraform"
  commit_author       = "Terraform"
  commit_email        = "terraform@example.com"
  overwrite_on_create = true

  lifecycle {
    ignore_changes = [
      commit_message,
      commit_author,
      commit_email,
    ]
  }

  depends_on = [
    github_actions_secret.gcp_workload_identity_provider,
    github_actions_secret.gcp_service_account,
    github_actions_secret.gcs_bucket_name,
    time_sleep.wait_for_wif_propagation
  ]
}

resource "github_repository_file" "readme" {
  count               = var.schema_repo_name != "" ? 1 : 0
  repository          = var.schema_repo_name
  branch              = "main"
  file                = "README.md"
  content             = file("${path.module}/templates/repo_readme.md")
  commit_message      = "Update README docs via Terraform"
  commit_author       = "Terraform"
  commit_email        = "terraform@example.com"
  overwrite_on_create = true

  lifecycle {
    ignore_changes = [
      commit_message,
      commit_author,
      commit_email,
    ]
  }
}


# --- Service Account for GitHub Actions ---
resource "google_service_account" "github_actions" {
  count        = var.schema_repo_name != "" ? 1 : 0
  account_id   = "github-actions-uploader"
  display_name = "GitHub Actions GCS Uploader"
}

resource "google_storage_bucket_iam_member" "github_actions_writer" {
  count  = var.schema_repo_name != "" ? 1 : 0
  bucket = google_storage_bucket.eventvalidator_schemas_bucket.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.github_actions[0].email}"
}

# --- Workload Identity Federation ---

resource "random_id" "wif_suffix" {
  count       = var.schema_repo_name != "" ? 1 : 0
  byte_length = 4
  keepers = {
    # If the project changes, we definitely need a new pool
    project_id = var.project_id
  }
}

resource "google_iam_workload_identity_pool" "github_pool" {
  count                     = var.schema_repo_name != "" ? 1 : 0
  workload_identity_pool_id = "gh-pool-${random_id.wif_suffix[0].hex}"
  display_name              = "GitHub Actions Pool ${random_id.wif_suffix[0].hex}"
  description               = "Identity pool for GitHub Actions"
}

resource "google_iam_workload_identity_pool_provider" "github_provider" {
  count                              = var.schema_repo_name != "" ? 1 : 0
  workload_identity_pool_id          = google_iam_workload_identity_pool.github_pool[0].workload_identity_pool_id
  workload_identity_pool_provider_id = "gh-provider-${random_id.wif_suffix[0].hex}"
  display_name                       = "GitHub Provider ${random_id.wif_suffix[0].hex}"
  description                        = "OIDC Provider for GitHub Actions"
  
  # Explicit condition required by API to avoid "condition must reference claims" error
  attribute_condition = "assertion.repository == '${var.schema_repo_owner}/${var.schema_repo_name}'"

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.actor"      = "assertion.actor"
    "attribute.repository" = "assertion.repository"
  }

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

# The Workload Identity setup in Google Cloud can take a couple of minutes to propagate
# globally. Without this delay, the GitHub workflow will trigger immediately on creation
# and fail with "invalid_target" errors on the first run.
resource "time_sleep" "wait_for_wif_propagation" {
  count           = var.schema_repo_name != "" ? 1 : 0
  depends_on      = [google_service_account_iam_member.workload_identity_user]
  create_duration = "90s"
}

# Grant the GitHub Actions identity access to impersonate the Service Account
# ONLY requests coming from the specific GitHub repository will be allowed.
resource "google_service_account_iam_member" "workload_identity_user" {
  count              = var.schema_repo_name != "" ? 1 : 0
  service_account_id = google_service_account.github_actions[0].name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github_pool[0].name}/attribute.repository/${var.schema_repo_owner}/${var.schema_repo_name}"
}

# --- GitHub Secrets ---

# We no longer need the private key. Instead, we provide the WIF configuration.

resource "github_actions_secret" "gcp_workload_identity_provider" {
  count           = var.schema_repo_name != "" ? 1 : 0
  repository      = var.schema_repo_name
  secret_name     = "GCP_WORKLOAD_IDENTITY_PROVIDER"
  plaintext_value = google_iam_workload_identity_pool_provider.github_provider[0].name
}

resource "github_actions_secret" "gcp_service_account" {
  count           = var.schema_repo_name != "" ? 1 : 0
  repository      = var.schema_repo_name
  secret_name     = "GCP_SERVICE_ACCOUNT"
  plaintext_value = google_service_account.github_actions[0].email
}

resource "github_actions_secret" "gcs_bucket_name" {
  count           = var.schema_repo_name != "" ? 1 : 0
  repository      = var.schema_repo_name
  secret_name     = "GCS_BUCKET_NAME"
  plaintext_value = google_storage_bucket.eventvalidator_schemas_bucket.name
}

# --- Branch Protection ---
resource "github_branch_protection" "main" {
  count         = var.schema_repo_name != "" && var.enable_branch_protection ? 1 : 0
  repository_id = var.schema_repo_name
  pattern       = "main"

  required_status_checks {
    strict   = true
    contexts = ["Validate Schemas"]
  }

  required_pull_request_reviews {
    dismiss_stale_reviews           = true
    required_approving_review_count = 0 # 0 allows merging your own PRs, but enforces the PR flow
  }
  
  enforce_admins = false
}
