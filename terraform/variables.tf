variable "project_id" {
  description = "GCP プロジェクトID"
  type        = string
}

variable "region" {
  description = "デプロイリージョン"
  type        = string
  default     = "asia-northeast1"
}

variable "github_owner" {
  description = "GitHub オーナー名（ユーザー名 or 組織名）。未設定の場合 Cloud Build Trigger は作成されない"
  type        = string
  default     = ""
}

variable "github_repo" {
  description = "GitHub リポジトリ名。未設定の場合 Cloud Build Trigger は作成されない"
  type        = string
  default     = ""
}

variable "github_branch" {
  description = "トリガー対象ブランチ"
  type        = string
  default     = "main"
}
