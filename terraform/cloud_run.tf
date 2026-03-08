# 推論サーバー用 Cloud Run サービス
# パイプラインの deploy_component がコンテナイメージと AIP_STORAGE_URI を更新する
resource "google_cloud_run_v2_service" "serving" {
  name     = "vtuber-detector"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.vertex_ai.email

    containers {
      # 初回は placeholder イメージ。パイプライン実行後に serving コンテナに差し替わる。
      image = "us-docker.pkg.dev/cloudrun/container/hello"

      env {
        name  = "AIP_STORAGE_URI"
        value = "gs://${var.project_id}-mlops-data/models/initial"
      }
      env {
        name  = "AIP_HEALTH_ROUTE"
        value = "/health"
      }
      env {
        name  = "AIP_PREDICT_ROUTE"
        value = "/predict"
      }

      ports {
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = "2"
          memory = "4Gi"
        }
      }
    }
  }

  # パイプラインが image と AIP_STORAGE_URI を動的に更新するため
  # terraform apply で上書きしないように ignore_changes を設定
  lifecycle {
    ignore_changes = [template]
  }

  depends_on = [google_project_service.apis]
}

# デモ用: 認証なしで /predict を呼べるようにする
resource "google_cloud_run_v2_service_iam_member" "public_invoker" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.serving.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

