terraform {
  required_providers {
    google = {
        source  = "hashicorp/google"
        version = "~> 6.0"
    }
    google-beta = {
        source  = "hashicorp/google-beta"
        version = "~> 6.0"
    }
    local = {
        source  = "hashicorp/local"
        version = ">= 2.1.0"
    }
  }
}

provider "google" {
  project               = var.project_id
  region                = var.region
  billing_project       = var.project_id
  user_project_override = true
  credentials           = var.credentials_file != "" ? file(var.credentials_file) : null
}

provider "google-beta" {
  project               = var.project_id
  region                = var.region
  billing_project       = var.project_id
  user_project_override = true
  credentials           = var.credentials_file != "" ? file(var.credentials_file) : null
}
