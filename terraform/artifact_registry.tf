# パイプラインコンポーネント用 Docker イメージの保存先
# Vertex AI Pipelines の各ステップで使うコンテナイメージを格納
resource "google_artifact_registry_repository" "mlops" {
  repository_id = "mlops"
  location      = var.region
  format        = "DOCKER"
  description   = "MLOps ハンズオン用コンテナイメージリポジトリ"

  depends_on = [google_project_service.apis]
}
