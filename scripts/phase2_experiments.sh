#!/usr/bin/env bash
# Phase 2: Vertex AI Custom Training Job を 2 件投入して実験結果を比較する
# epochs=3 と epochs=5 の 2 ジョブを非同期で投入する
#
# 使い方:
#   export PROJECT_ID=<your-project>
#   bash scripts/phase2_experiments.sh
set -euo pipefail
# shellcheck source=scripts/common.sh
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

log "Phase 2: Custom Training Job を投入 (epochs=3, epochs=5)"
check_project_id

cd "${PROJECT_ROOT}"
activate_venv

export PROJECT_ID REGION
python src/submit_job.py

ok "2 件のジョブを非同期投入しました (epochs=3 / epochs=5)"
echo "     学習の進捗 : https://console.cloud.google.com/vertex-ai/training/custom-jobs"
echo "     実験結果比較: https://console.cloud.google.com/vertex-ai/experiments"
