# Cloud Build Trigger
# pipeline/config.yaml が main ブランチへ Push されたときに自動発火する
#
# 前提: GitHubリポジトリとのOAuth接続は事前にコンソールで設定が必要
# 手順: Cloud Build → Triggers → Connect Repository
# github_owner / github_repo が両方設定されている場合のみ作成
resource "google_cloudbuild_trigger" "mlops_pipeline" {
  count = (var.github_owner != "" && var.github_repo != "") ? 1 : 0
  name        = "mlops-pipeline-trigger"
  description = "config.yaml の変更を検知してVTuber検出パイプラインを自動実行"
  location    = "global"

  github {
    owner = var.github_owner
    name  = var.github_repo
    push {
      branch = "^${var.github_branch}$"
    }
  }

  # config.yaml の変更のみをトリガー条件にする
  # 他のファイル（アプリコード等）を変えてもパイプラインは走らない
  included_files = ["pipeline/config.yaml"]

  filename = "cloudbuild.yaml"

  service_account = google_service_account.cloud_build.id

  substitutions = {
    _PROJECT_ID  = var.project_id
    _REGION      = var.region
    _ENDPOINT_ID = google_cloud_run_v2_service.serving.name
  }

  depends_on = [
    google_project_service.apis,
    google_service_account.cloud_build,
  ]
}
