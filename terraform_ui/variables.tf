variable "project_id" {
  description = "The ID of the project in which to create the resources."
  type        = string
}

variable "region" {
  description = "The region in which to create the resources."
  type        = string
}

variable "credentials_file" {
  description = "The name of the credentials file."
  type        = string
}

# --- Backend Integration ---

variable "schemas_bucket" {
  description = "The GCS bucket name for event schemas (from terraform_backend output)"
  type        = string
}

variable "bq_dataset" {
  description = "The BigQuery dataset ID (from terraform_backend output)"
  type        = string
  default     = "event_data_dataset"
}

variable "bq_table" {
  description = "The BigQuery table ID (from terraform_backend output)"
  type        = string
  default     = "event_data_table"
}

# --- IAP & Cloud Run Variables ---

variable "iap_client_id" {
  description = "OAuth 2.0 Client ID for IAP"
  type        = string
  sensitive   = true
}

variable "iap_client_secret" {
  description = "OAuth 2.0 Client Secret for IAP"
  type        = string
  sensitive   = true
}

variable "authorized_users" {
  description = "List of users authorized to access the app via IAP (e.g. user:email@example.com)"
  type        = list(string)
}

variable "streamlit_image_tag" {
  description = "Tag of the Streamlit Docker image to deploy"
  type        = string
  default     = "latest"
}

# --- GitHub Integration ---
variable "github_token" {
  description = "GitHub Personal Access Token for schema sync"
  type        = string
  sensitive   = true
  default     = ""
}

variable "schema_repo_owner" {
  description = "Owner of the schema repository (user or org)"
  type        = string
  default     = ""
}

variable "schema_repo_name" {
  description = "Name of the schema repository"
  type        = string
  default     = ""
}

variable "schema_repo_path" {
  description = "Path to schemas within the repository"
  type        = string
  default     = "schemas"
}

variable "schema_repo_branch" {
  description = "Default branch for the schema repository"
  type        = string
  default     = "main"
}

variable "use_classic_load_balancer" {
  description = "If true, creates a classic Global Load Balancer (costly). If false, uses Direct IAP Integration (Preview) or pure Proxy/IAM."
  type        = bool
  default     = false
}
