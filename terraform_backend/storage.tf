resource "random_id" "bucket_suffix" {
  byte_length = 4
}

resource "google_storage_bucket" "eventvalidatorfunction_bucket" {
  name     = "event_validator_function_source_bucket-${random_id.bucket_suffix.hex}"
  location = var.location
  provider = google

}

resource "google_storage_bucket" "eventvalidator_schemas_bucket" {
  name     = "event_validator_schemas_bucket-${random_id.bucket_suffix.hex}"
  location = var.location
  provider = google
  force_destroy = var.force_destroy_buckets

}

resource "google_storage_bucket_object" "eventvalidatorfunction_object" {
  name   = "cf-${archive_file.function_zip.output_sha}.zip"
  bucket = google_storage_bucket.eventvalidatorfunction_bucket.name
  source = archive_file.function_zip.output_path
  provider = google
}


# 3. Initial Data (GA4 Recommended)

# Batch upload all 36 recommended schemas
resource "google_storage_bucket_object" "initial_schemas" {
  for_each = fileset("${path.module}/src/GA4 Recommended/schemas/", "*.json")

  name   = each.value
  source = "${path.module}/src/GA4 Recommended/schemas/${each.value}"
  bucket = google_storage_bucket.eventvalidator_schemas_bucket.name
}

# Upload the master repository file
resource "google_storage_bucket_object" "ga4_repo_json" {
  name   = "repo.json"
  bucket = google_storage_bucket.eventvalidator_schemas_bucket.name
  source = "${path.module}/src/GA4 Recommended/repo.json"
}
