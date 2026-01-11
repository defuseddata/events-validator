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
    local = {
        source  = "hashicorp/local"
        version = ">= 2.1.0"
    }
    time = {
        source  = "hashicorp/time"
        version = ">= 0.9.0"
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
