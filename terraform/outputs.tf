output "project_id" {
  value = var.project_id
}

output "region" {
  value = var.region
}

output "data_bucket" {
  value = google_storage_bucket.mlops_data.name
}

output "pipeline_bucket" {
  value = google_storage_bucket.pipeline_root.name
}

output "artifact_registry_repo" {
  value = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.mlops.repository_id}"
}

output "vertex_ai_service_account" {
  value = google_service_account.vertex_ai.email
}

output "serving_url" {
  value = google_cloud_run_v2_service.serving.uri
}
