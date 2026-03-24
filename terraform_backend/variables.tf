variable "project_id" {
  description = "The ID of the project in which to create the resources."
  type        = string
}

variable "region" {
  description = "The region in which to create the resources."
  type        = string
}

variable "credentials_file" {
  description = "Path to the service account JSON key for manual deployments. If empty, Application Default Credentials will be used."
  type        = string
  default     = ""
}

variable "function_source_dir" {
  description = "The source directory for the cloud function."
  type        = string
}

variable "location" {
  description = "The location for resources."
  type        = string
}

variable "bq_schema_file" {
  description = "BigQuery schema file path"
  type        = string
}

variable "LOG_PAYLOAD_WHEN_ERROR_FLAG" {
  description = "Do you want to log payload when validation fails? (true/false)"
  type        = bool
}

variable "LOG_PAYLOAD_WHEN_VALID_FLAG" {
  description = "Do you want to log payload when validation passes? (true/false)"
  type        = bool
}

variable "LOG_VALID_FIELDS_FLAG" {
  description = "Do you want to log valid fields into bigquery? (true/false)"
  type        = bool
}

variable "EVENT_DATA_PATH" {
  description = "Path to event data in request"
  type        = string
}

variable "EVENT_NAME_ATTRIBUTE" {
  description = "Attribute in event data that contains event name"
  type        = string
}

variable "deletion_protection" {
  description = "Protect resource from deletion"
  type        = bool
  default     = false
}

variable "force_destroy_buckets" {
  description = "Allow deletion of buckets even if they contain objects"
  type        = bool
  default     = false
}

variable "backend_min_instances" {
  description = "Minimum number of instances for the Cloud Function"
  type        = number
  default     = 0
}

variable "backend_max_instances" {
  description = "Maximum number of instances for the Cloud Function"
  type        = number
  default     = 10
}
