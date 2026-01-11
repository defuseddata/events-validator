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
  description = "List of emails (users/groups) authorized to access the UI via IAP"
  type        = list(string)
  default     = []
}

variable "streamlit_image_tag" {
  description = "The tag of the image to deploy for the Streamlit UI"
  type        = string
  default     = "latest"
}
