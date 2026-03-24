resource "google_artifact_registry_repository" "streamlit_repo" {
  location      = var.region
  repository_id = "event-validator-ui-repo"
  description   = "Docker repository for Streamlit UI"
  format        = "DOCKER"
  depends_on    = [google_project_service.required_services]
}

resource "google_cloud_run_v2_service" "streamlit_ui" {
  name     = "event-validator-ui"
  location = var.region
  provider = google-beta
  ingress      = var.use_classic_load_balancer ? "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER" : "INGRESS_TRAFFIC_ALL"
  launch_stage = var.use_classic_load_balancer ? "GA" : "BETA"
  iap_enabled  = var.use_classic_load_balancer ? false : true
  depends_on = [google_artifact_registry_repository.streamlit_repo]
  
  template {
    scaling {
      min_instance_count = var.ui_min_instances
      max_instance_count = var.ui_max_instances
    }
    service_account = google_service_account.streamlit_worker.email
    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.streamlit_repo.repository_id}/event-validator-ui:${var.streamlit_image_tag}"
      ports {
        container_port = 8080
      }
      env {
        name  = "BUCKET_NAME"
        value = var.schemas_bucket
      }
      env {
        name  = "GCP_PROJECT"
        value = var.project_id
      }
      env {
        name  = "REPO_JSON_FILE"
        value = "repo.json"
      }
      env {
        name  = "BQ_DATASET"
        value = var.bq_dataset
      }
      env {
        name  = "BQ_TABLE"
        value = var.bq_table
      }
      env {
        name  = "GITHUB_TOKEN"
        value = var.github_token
      }
      env {
        name  = "SCHEMA_REPO_OWNER"
        value = var.schema_repo_owner
      }
      env {
        name  = "SCHEMA_REPO_NAME"
        value = var.schema_repo_name
      }
      env {
        name  = "SCHEMA_REPO_PATH"
        value = var.schema_repo_path
      }
      env {
        name  = "SCHEMA_REPO_DEFAULT_BRANCH"
        value = var.schema_repo_branch
      }
    }
  }
}



# Reserved Global static IP
resource "google_compute_global_address" "streamlit_lb_ip" {
  count = var.use_classic_load_balancer ? 1 : 0
  name  = "event-validator-lb-ip"
}

# Serverless NEG (Network Endpoint Group) points to Cloud Run
resource "google_compute_region_network_endpoint_group" "streamlit_neg" {
  count                 = var.use_classic_load_balancer ? 1 : 0
  name                  = "streamlit-neg"
  network_endpoint_type = "SERVERLESS"
  region                = var.region
  cloud_run {
    service = google_cloud_run_v2_service.streamlit_ui.name
  }
}

# Backend Service with IAP
resource "google_compute_backend_service" "streamlit_backend" {
  count                 = var.use_classic_load_balancer ? 1 : 0
  name                  = "streamlit-backend-service"
  protocol              = "HTTPS"
  load_balancing_scheme = "EXTERNAL_MANAGED"

  backend {
    group = google_compute_region_network_endpoint_group.streamlit_neg[0].id
  }

  iap {
    enabled              = true
    oauth2_client_id     = var.iap_client_id
    oauth2_client_secret = var.iap_client_secret
  }
}

# URL Map
resource "google_compute_url_map" "streamlit_lb_url_map" {
  count           = var.use_classic_load_balancer ? 1 : 0
  name            = "streamlit-url-map"
  default_service = google_compute_backend_service.streamlit_backend[0].id
}

# Managed SSL Certificate (Requires a domain)
# We use [IP].sslip.io for easy automation
resource "google_compute_managed_ssl_certificate" "streamlit_cert" {
  count = var.use_classic_load_balancer ? 1 : 0
  name  = "streamlit-ssl-cert"
  managed {
    domains = ["${google_compute_global_address.streamlit_lb_ip[0].address}.sslip.io"]
  }
}

# HTTPS Proxy
resource "google_compute_target_https_proxy" "streamlit_https_proxy" {
  count            = var.use_classic_load_balancer ? 1 : 0
  name             = "streamlit-https-proxy"
  url_map          = google_compute_url_map.streamlit_lb_url_map[0].id
  ssl_certificates = [google_compute_managed_ssl_certificate.streamlit_cert[0].id]
}

# Global Forwarding Rule
resource "google_compute_global_forwarding_rule" "streamlit_forwarding_rule" {
  count                 = var.use_classic_load_balancer ? 1 : 0
  name                  = "streamlit-forwarding-rule"
  target                = google_compute_target_https_proxy.streamlit_https_proxy[0].id
  port_range            = "443"
  ip_address            = google_compute_global_address.streamlit_lb_ip[0].address
  load_balancing_scheme = "EXTERNAL_MANAGED"
}

# 4. IAP Access Control

# Allow specific users to access through IAP at the Backend Service level
resource "google_iap_web_backend_service_iam_binding" "iap_access_lb" {
  count               = var.use_classic_load_balancer ? 1 : 0
  project             = var.project_id
  web_backend_service = google_compute_backend_service.streamlit_backend[0].name
  role                = "roles/iap.httpsResourceAccessor"
  members             = var.authorized_users
}

# Ensure Cloud Run service is accessible from the LB
resource "google_cloud_run_v2_service_iam_member" "lb_access" {
  count    = var.use_classic_load_balancer ? 1 : 0
  location = google_cloud_run_v2_service.streamlit_ui.location
  name     = google_cloud_run_v2_service.streamlit_ui.name
  role     = "roles/run.invoker"
  member   = "allUsers" # Limited by IAP at the LB level
}
