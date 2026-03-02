# ─────────────────────────────────────────
# Cloud Build 用サービスアカウント
# パイプライン投入・コンテナビルド・GCS読み書きを担う
# ─────────────────────────────────────────
resource "google_service_account" "cloud_build" {
  account_id   = "mlops-cloud-build"
  display_name = "MLOps Cloud Build SA"
  description  = "Cloud Build が Vertex AI Pipelines を投入するためのSA"
}

resource "google_project_iam_member" "cloud_build_aiplatform" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.cloud_build.email}"
}

resource "google_project_iam_member" "cloud_build_storage" {
  project = var.project_id
  role    = "roles/storage.admin"
  member  = "serviceAccount:${google_service_account.cloud_build.email}"
}

resource "google_project_iam_member" "cloud_build_artifact_registry" {
  project = var.project_id
  role    = "roles/artifactregistry.writer"
  member  = "serviceAccount:${google_service_account.cloud_build.email}"
}

resource "google_project_iam_member" "cloud_build_logs" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.cloud_build.email}"
}

# Cloud Build のデフォルトSAにも同様の権限を付与
# （Cloud Build Triggerはデフォルトでプロジェクト番号@cloudbuild.gserviceaccount.comを使う）
data "google_project" "project" {}

resource "google_project_iam_member" "cloud_build_default_aiplatform" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${data.google_project.project.number}@cloudbuild.gserviceaccount.com"

  # Cloud Build APIが有効になってからSAが作られるため依存関係を明示
  depends_on = [google_project_service.apis]
}

resource "google_project_iam_member" "cloud_build_default_storage" {
  project = var.project_id
  role    = "roles/storage.admin"
  member  = "serviceAccount:${data.google_project.project.number}@cloudbuild.gserviceaccount.com"

  depends_on = [google_project_service.apis]
}

# ─────────────────────────────────────────
# Vertex AI 用サービスアカウント
# Custom Training Job・Pipelines の各ステップが使う
# ─────────────────────────────────────────
resource "google_service_account" "vertex_ai" {
  account_id   = "mlops-vertex-ai"
  display_name = "MLOps Vertex AI SA"
  description  = "Vertex AI が学習・デプロイ時にGCSやModel Registryを操作するSA"
}

resource "google_project_iam_member" "vertex_ai_storage" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.vertex_ai.email}"
}

resource "google_project_iam_member" "vertex_ai_aiplatform" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.vertex_ai.email}"
}

resource "google_project_iam_member" "vertex_ai_artifact_registry" {
  project = var.project_id
  role    = "roles/artifactregistry.reader"
  member  = "serviceAccount:${google_service_account.vertex_ai.email}"
}

# ─────────────────────────────────────────
# Cloud Run 用サービスアカウント
# Streamlit アプリが Vertex AI Endpoint を呼び出す
# ─────────────────────────────────────────
resource "google_service_account" "cloud_run" {
  account_id   = "mlops-cloud-run"
  display_name = "MLOps Cloud Run SA"
  description  = "Streamlit アプリが Vertex AI Endpoint へ推論リクエストを送るSA"
}

resource "google_project_iam_member" "cloud_run_aiplatform" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.cloud_run.email}"
}
