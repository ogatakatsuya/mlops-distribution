# Vertex AI Endpoint
# モデルの推論APIの口。IDを固定することで、モデルを更新しても
# アプリ側のコード（ENDPOINT_ID）を変更せずにシームレスに切り替え可能。
resource "google_vertex_ai_endpoint" "vtuber_detector" {
  name         = "vtuber-detector"
  display_name = "VTuber Detector Endpoint"
  location     = var.region
  description  = "VTuberキャラクター検出モデルのエンドポイント。パイプラインが自動更新する。"

  depends_on = [google_project_service.apis]
}
