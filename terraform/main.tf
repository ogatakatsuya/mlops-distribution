terraform {
  required_version = ">= 1.5"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# ハンズオンで使う GCP APIs を一括有効化
resource "google_project_service" "apis" {
  for_each = toset([
    "aiplatform.googleapis.com",       # Vertex AI (学習・デプロイ・Pipelines)
    "storage.googleapis.com",          # Cloud Storage (データ・モデル保管)
    "cloudbuild.googleapis.com",       # Cloud Build (CI/CD トリガー)
    "artifactregistry.googleapis.com", # Artifact Registry (Dockerイメージ)
    "run.googleapis.com",              # Cloud Run (アプリケーション)
  ])

  service            = each.value
  disable_on_destroy = false
}
