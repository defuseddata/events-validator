
data "google_project" "project" {
  project_id = var.project_id
}

# Allow authorized users to invoke Cloud Run (needed for both LB and Direct modes)
resource "google_cloud_run_v2_service_iam_member" "authorized_invokers" {
  for_each = toset(var.authorized_users)
  location = google_cloud_run_v2_service.streamlit_ui.location
  name     = google_cloud_run_v2_service.streamlit_ui.name
  role     = "roles/run.invoker"
  member   = each.value
}

# Allow IAP Service Agent to invoke Cloud Run (required for Direct Integration)
resource "google_cloud_run_v2_service_iam_member" "iap_agent_invoker" {
  count    = var.use_classic_load_balancer ? 0 : 1
  location = google_cloud_run_v2_service.streamlit_ui.location
  name     = google_cloud_run_v2_service.streamlit_ui.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-iap.iam.gserviceaccount.com"
}

# Allow specific users to access ALL IAP-secured Web apps in this project
# Only needed for Direct IAP Integration
resource "google_iap_web_iam_binding" "iap_access" {
  count    = var.use_classic_load_balancer ? 0 : 1
  provider = google-beta
  project  = var.project_id
  role     = "roles/iap.httpsResourceAccessor"
  members  = var.authorized_users
}


