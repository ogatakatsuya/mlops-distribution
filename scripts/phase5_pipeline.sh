#!/usr/bin/env bash
# Phase 5: Cloud Build を手動で即時実行する (git push せずにパイプラインをテストする場合)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/terraform"

PROJECT_ID=$(terraform output -raw project_id)
REGION=$(terraform output -raw region)
ENDPOINT_ID="vtuber-detector"

cd "$ROOT"

echo "=== Phase 5: Manual Cloud Build Submit ==="
echo "  Project  : $PROJECT_ID"
echo "  Region   : $REGION"
echo "  Endpoint : $ENDPOINT_ID"
echo ""

gcloud builds submit \
  --project="$PROJECT_ID" \
  --config=cloudbuild.yaml \
  --substitutions="_PROJECT_ID=${PROJECT_ID},_REGION=${REGION},_ENDPOINT_ID=${ENDPOINT_ID},_WANDB_API_KEY=${WANDB_API_KEY:-},_WANDB_PROJECT=${WANDB_PROJECT:-vtuber-detector}" \
  .

echo ""
echo "=== 完了 ==="
