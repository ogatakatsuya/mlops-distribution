# terraform apply 後にここに表示される値を環境変数に設定して使う
# export PROJECT_ID=$(terraform output -raw project_id)
# export ENDPOINT_ID=$(terraform output -raw endpoint_id)

output "project_id" {
  description = "GCP プロジェクトID"
  value       = var.project_id
}

output "region" {
  description = "デプロイリージョン"
  value       = var.region
}

output "data_bucket" {
  description = "データセット・モデル保存用 GCS バケット名"
  value       = google_storage_bucket.mlops_data.name
}

output "pipeline_bucket" {
  description = "Vertex AI Pipelines ルート用 GCS バケット名"
  value       = google_storage_bucket.pipeline_root.name
}

output "artifact_registry_repo" {
  description = "Artifact Registry リポジトリ URI（docker push 先）"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.mlops.repository_id}"
}

output "endpoint_id" {
  description = "Vertex AI Endpoint ID（アプリ・パイプラインから参照）"
  value       = google_vertex_ai_endpoint.vtuber_detector.id
}

output "endpoint_name" {
  description = "Vertex AI Endpoint フルリソース名"
  value       = google_vertex_ai_endpoint.vtuber_detector.name
}

output "vertex_ai_service_account" {
  description = "Vertex AI 用サービスアカウント（パイプライン投入時に指定）"
  value       = google_service_account.vertex_ai.email
}

output "next_steps" {
  description = "terraform apply 後の次のステップ"
  value       = <<-EOT
    ✅ インフラ構築完了！次のステップ:

    1. データセットのアップロード:
       gsutil -m cp -r vtuber_dataset/ gs://${google_storage_bucket.mlops_data.name}/datasets/v1/

    2. 環境変数の設定:
       export PROJECT_ID=${var.project_id}
       export REGION=${var.region}
       export ENDPOINT_ID=${google_vertex_ai_endpoint.vtuber_detector.name}

    3. Phase 2: Vertex AI Custom Training Job で学習を実行 (epochs=3, epochs=5)
       python src/submit_job.py

    ※ アプリはローカルで動作させる。MLOpsの責務はEndpointへの自動デプロイまで。
  EOT
}
