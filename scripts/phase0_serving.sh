#!/usr/bin/env bash
# Phase 0: YOLO 推論コンテナをビルドして Artifact Registry へプッシュする
# ※ モデルが変わっても推論ロジックが変わらない限り再実行不要
#
# 使い方:
#   export PROJECT_ID=<your-project>
#   bash scripts/phase0_serving.sh
set -euo pipefail
# shellcheck source=scripts/common.sh
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

log "Phase 0-B: 推論コンテナをビルド & Artifact Registry へプッシュ"
check_project_id

cd "${PROJECT_ROOT}"

# Docker が Artifact Registry に push できるよう認証
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet

# Apple Silicon (M1/M2/M3) でも Vertex AI (x86_64) で動くよう --platform 指定
docker build --platform linux/amd64 -t "${SERVING_IMAGE}" serve/
docker push "${SERVING_IMAGE}"

ok "Pushed: ${SERVING_IMAGE}"
