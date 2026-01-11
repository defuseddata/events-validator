resource "google_project_service" "required_services" {
  for_each = toset([
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "compute.googleapis.com",
    "iap.googleapis.com"
  ])

  project = var.project_id
  service = each.value
}
