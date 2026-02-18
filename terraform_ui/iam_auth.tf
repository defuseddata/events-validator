
# Allow specific users to invoke Cloud Run directly (IAM Auth)
resource "google_cloud_run_v2_service_iam_binding" "direct_access" {
  location = google_cloud_run_v2_service.streamlit_ui.location
  name     = google_cloud_run_v2_service.streamlit_ui.name
  role     = "roles/run.invoker"
  members  = concat(
    var.authorized_users,
    # Include IAP Service Agent only if Classic LB is NOT used (Direct Integration)
    var.use_classic_load_balancer ? [] : ["serviceAccount:service-836240319875@gcp-sa-iap.iam.gserviceaccount.com"]
  )
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


