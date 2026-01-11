output "api_gateway_full_service_name" {
  value = "${google_api_gateway_api.gateway.api_id}.apigateway.googleapis.com"
  depends_on = [ google_api_gateway_api.gateway ]
}

output "api_gateway_url" {
  description = "value is the URL of the API Gateway"
    value = google_api_gateway_gateway.api_gateway.default_hostname
    depends_on = [ google_api_gateway_api.gateway ]
}

output "api_key" {
  description = "value is the API key for the API Gateway"
    value = google_apikeys_key.gateway_key.key_string
    sensitive = true
    depends_on = [ google_apikeys_key.gateway_key ]
}

output "schemas_bucket" {
    description = "The GCS bucket to store event schemas"
    value = google_storage_bucket.eventvalidator_schemas_bucket.name
    depends_on = [ google_storage_bucket.eventvalidator_schemas_bucket ]
}

output "bq_dataset" {
    description = "The BigQuery dataset ID"
    value = google_bigquery_dataset.event_validator_dataset.dataset_id
}

output "bq_table" {
    description = "The BigQuery table ID"
    value = google_bigquery_table.event_validator_data_table.table_id
}
