resource "google_api_gateway_api" "gateway" {
    api_id = "my-api"
    display_name = "api-gateway"
    provider = google-beta
    depends_on = [
        google_project_service.required_services["cloudfunctions.googleapis.com"]
        ]
}

resource "time_sleep" "wait_for_api_propagation" {
  create_duration = "60s"

  depends_on = [google_api_gateway_api.gateway]
}

resource "google_project_service" "api_gateway_managed_service" {
  project = var.project_id
  service = google_api_gateway_api.gateway.managed_service
  disable_on_destroy = false

  depends_on = [time_sleep.wait_for_api_propagation]
}


resource "random_id" "gateway_config_suffix" {
  byte_length = 2
}

resource "random_id" "api_key_suffix" {
  byte_length = 4
}

resource "google_apikeys_key" "gateway_key" {
  name         = "gateway-key-${random_id.api_key_suffix.hex}"
  display_name = "gateway-key-${random_id.api_key_suffix.hex}"
  project      = var.project_id

  restrictions {
    api_targets {
      service = google_api_gateway_api.gateway.managed_service
  }
}

  depends_on = [
    google_project_service.required_services["apikeys.googleapis.com"]
  ]
}

locals {
  rendered_openapi = templatefile("${path.module}/src/templates/gateway_config_template.yaml.tpl", {
    region        = var.region
    project       = var.project_id
    function_name = google_cloudfunctions2_function.function.name
    api_key       = google_apikeys_key.gateway_key.key_string
    run_uri  = google_cloudfunctions2_function.function.service_config[0].uri
  })
}

resource "google_api_gateway_api_config" "api_cfg" {
  provider = google-beta
  api = google_api_gateway_api.gateway.api_id
  api_config_id = "config-${substr(md5(local.rendered_openapi), 0, 6)}" #compare content hash to avoid duplicates

  openapi_documents {
    document {
      path     = "${path.module}/src/gateway_config/gateway_openapi${random_id.gateway_config_suffix.hex}.yaml"
      contents = base64encode( local.rendered_openapi)
    }
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "google_api_gateway_gateway" "api_gateway" {
  provider = google-beta
  api_config = google_api_gateway_api_config.api_cfg.id
  gateway_id = "my-gateway"
}

data "google_project" "project" {
  project_id = var.project_id
}

resource "google_cloud_run_service_iam_member" "gateway_invoker" {
  project  = var.project_id
  location = var.region
  service  = google_cloudfunctions2_function.function.service_config[0].service

  role   = "roles/run.invoker"
  member = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-apigateway.iam.gserviceaccount.com"

  depends_on = [ google_cloudfunctions2_function.function ]
}
