resource "google_project_service" "required_services" {
  for_each = toset([
    "cloudfunctions.googleapis.com",
    "run.googleapis.com",
    "cloudbuild.googleapis.com",
    "storage.googleapis.com",
    "apigateway.googleapis.com",
    "servicecontrol.googleapis.com",
    "apikeys.googleapis.com",
    "bigquery.googleapis.com"
  ])

  project = var.project_id
  service = each.value
}
