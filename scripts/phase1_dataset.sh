#!/usr/bin/env bash
# Phase 1: ローカルのデータセットを Cloud Storage に同期する
#
# 前提: preprocess/distill.py を実行して vtuber_dataset/ を生成済みであること
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/terraform"

PROJECT_ID=$(terraform output -raw project_id)
DATA_BUCKET=$(terraform output -raw data_bucket)

DATASET_LOCAL="$ROOT/vtuber_dataset"
DATASET_VERSION="${DATASET_VERSION:-v1}"

if [ ! -d "$DATASET_LOCAL" ]; then
  echo "ERROR: vtuber_dataset/ が見つかりません"
  echo "先に preprocess/distill.py を実行してデータセットを生成してください"
  exit 1
fi

echo "=== Phase 1: Dataset Upload ==="
echo "  ローカル : $DATASET_LOCAL"
echo "  GCS     : gs://${DATA_BUCKET}/datasets/${DATASET_VERSION}/"
echo ""

gcloud storage rsync -r \
  "$DATASET_LOCAL/" \
  "gs://${DATA_BUCKET}/datasets/${DATASET_VERSION}/"

echo ""
echo "=== 完了 ==="
echo "pipeline/config.yaml の dataset.version を ${DATASET_VERSION} に設定して phase5 を実行してください"
