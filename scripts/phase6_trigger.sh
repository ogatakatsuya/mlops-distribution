#!/usr/bin/env bash
# Phase 6: Cloud Build Trigger を追加して自動化を有効にする
# GitHub への Push だけでパイプラインが自動実行されるようになる
#
# 前提: Cloud Build コンソールで GitHub リポジトリとの OAuth 接続が必要
#       Cloud Build → Triggers → Connect Repository
#
# 使い方:
#   export GITHUB_OWNER=<github-username>
#   export GITHUB_REPO=<repo-name>
#   bash scripts/phase6_trigger.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/terraform"

PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${REGION:-asia-northeast1}"

[ -n "${GITHUB_OWNER:-}" ] || { echo "ERROR: GITHUB_OWNER が未設定です"; exit 1; }
[ -n "${GITHUB_REPO:-}"  ] || { echo "ERROR: GITHUB_REPO が未設定です"; exit 1; }

echo "=== Phase 6: Cloud Build Trigger ==="
echo "  GitHub : ${GITHUB_OWNER}/${GITHUB_REPO}"
echo ""

terraform apply \
  -auto-approve \
  -input=false \
  -var="project_id=${PROJECT_ID}" \
  -var="region=${REGION}" \
  -var="github_owner=${GITHUB_OWNER}" \
  -var="github_repo=${GITHUB_REPO}" \
  -var="github_branch=${GITHUB_BRANCH:-main}"

echo ""
echo "=== 完了 ==="
echo "pipeline/config.yaml を変更して git push するだけでパイプラインが自動実行されます。"
echo "確認: https://console.cloud.google.com/cloud-build/builds"
