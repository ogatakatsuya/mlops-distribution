#!/usr/bin/env bash
# Phase 5: Vertex AI Pipeline をコンパイルして投入する
# train → evaluate → register → deploy の全ステップが自動実行される
#
# 使い方:
#   export PROJECT_ID=<your-project>
#   bash scripts/phase5_pipeline.sh
set -euo pipefail
# shellcheck source=scripts/common.sh
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

log "Phase 5: Vertex AI Pipeline を投入"
check_project_id

cd "${PROJECT_ROOT}"
activate_venv

# パイプラインの学習コンポーネントが参照する train.py を GCS へ配置
gsutil cp src/train.py "gs://${DATA_BUCKET}/scripts/train.py"
ok "src/train.py → gs://${DATA_BUCKET}/scripts/train.py"

# ENDPOINT_ID は terraform output から取得
ENDPOINT_ID="$(get_endpoint_id)"

python pipeline/definition.py \
  --project_id="${PROJECT_ID}" \
  --region="${REGION}"         \
  --endpoint_id="${ENDPOINT_ID}"

ok "パイプラインを投入しました"
echo "     パイプライン進捗: https://console.cloud.google.com/vertex-ai/pipelines"
echo "     Endpoint 確認  : https://console.cloud.google.com/vertex-ai/endpoints"
