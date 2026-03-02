# MLOps ハンズオン用 GCS バケット
# datasets/, models/, pipeline-runs/ をまとめて1バケットで管理
resource "google_storage_bucket" "mlops_data" {
  name          = "${var.project_id}-mlops-data"
  location      = var.region
  force_destroy = true # ハンズオン終了後の削除を容易にする

  # バケットレベルでアクセス制御（オブジェクト単位のACLを無効化）
  uniform_bucket_level_access = true

  versioning {
    enabled = true # データセット・モデルのバージョン管理
  }

  # データセット・モデルの構造を示すフォルダ定義（実体はオブジェクト）
  # 実際のアップロードは gsutil or Python SDK で行う
}

# パイプライン定義ファイル（pipeline.json）の保存先
# Vertex AI Pipelines が参照する
resource "google_storage_bucket" "pipeline_root" {
  name          = "${var.project_id}-mlops-pipeline"
  location      = var.region
  force_destroy = true

  uniform_bucket_level_access = true
}
