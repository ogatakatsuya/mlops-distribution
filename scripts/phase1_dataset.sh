#!/usr/bin/env bash
# Phase 1: vtuber_dataset/ を GCS へアップロードする
# gsutil rsync を使うため冪等（差分のみ転送）
#
# 使い方:
#   export PROJECT_ID=<your-project>
#   bash scripts/phase1_dataset.sh
set -euo pipefail
# shellcheck source=scripts/common.sh
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

log "Phase 1: データセットを GCS へアップロード"
check_project_id

cd "${PROJECT_ROOT}"

[[ -d vtuber_dataset ]] || err "vtuber_dataset/ ディレクトリが見つかりません"

gsutil -m rsync -r -d vtuber_dataset/ "gs://${DATA_BUCKET}/datasets/v1/"

ok "gs://${DATA_BUCKET}/datasets/v1/ へアップロード完了"
echo "     GCS コンソール: https://console.cloud.google.com/storage/browser/${DATA_BUCKET}/datasets"
