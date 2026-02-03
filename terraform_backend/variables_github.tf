variable "github_token" {
  description = "GitHub Personal Access Token"
  type        = string
  sensitive   = true
}

variable "schema_repo_owner" {
  description = "Owner of the schema repository"
  type        = string
}

variable "schema_repo_name" {
  description = "Name of the schema repository"
  type        = string
}
