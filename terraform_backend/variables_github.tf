variable "github_token" {
  description = "GitHub Personal Access Token"
  type        = string
  sensitive   = true
  default     = ""
}

variable "schema_repo_owner" {
  description = "Owner of the schema repository"
  type        = string
  default     = ""
}

variable "schema_repo_name" {
  description = "Name of the schema repository"
  type        = string
  default     = ""
}

variable "enable_branch_protection" {
  description = "Enable GitHub Branch Protection (Requires GitHub Pro/Team for private repos or Public visibility)"
  type        = bool
  default     = false
}
