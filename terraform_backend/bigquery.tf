resource "google_bigquery_dataset" "event_validator_dataset" {
  dataset_id = "event_data_dataset"
  location   = var.location
  provider   = google

}

resource "google_bigquery_table" "event_validator_data_table" {
    dataset_id = google_bigquery_dataset.event_validator_dataset.dataset_id
    table_id   = "event_data_table"
    provider   = google

    schema = file("${path.module}/${var.bq_schema_file}")

    deletion_protection = var.deletion_protection
}
