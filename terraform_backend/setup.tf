terraform {
  required_providers {
    google = {
        source  = "hashicorp/google"
        version = ">= 4.0.0"
    }
    google-beta = {
        source  = "hashicorp/google-beta"
        version = ">= 4.0.0"
    }
    github = {
      source  = "integrations/github"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
  credentials = file("${path.module}/${var.credentials_file}")
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
  credentials = file("${path.module}/${var.credentials_file}")
}

provider "random" {
}

provider "archive" {
}

provider "github" {
  token = var.github_token
  owner = var.schema_repo_owner
}
