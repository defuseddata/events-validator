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

    # Partition on date_utc so date-range queries (validation report) only scan
    # the days they actually need, instead of the whole table.
    time_partitioning {
        type  = "DAY"
        field = "date_utc"
    }

    # Cluster on the columns the report filters/groups by (event_name, field).
    clustering = ["event_name", "field"]

    deletion_protection = var.deletion_protection
}
