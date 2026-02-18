output "streamlit_ui_url" {
  description = "The public URL of the Streamlit UI"
  value       = var.use_classic_load_balancer ? "https://${google_compute_global_address.streamlit_lb_ip[0].address}.sslip.io" : google_cloud_run_v2_service.streamlit_ui.uri
}

output "streamlit_build_command" {
  description = "The exact gcloud command to build and push the UI image"
  value       = "gcloud builds submit --region=${var.region} --tag ${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.streamlit_repo.repository_id}/event-validator-ui:${var.streamlit_image_tag} ./streamlit_ev"
}

output "streamlit_service_account" {
  description = "The service account email used by the Streamlit UI"
  value       = google_service_account.streamlit_worker.email
}
