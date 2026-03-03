#!/usr/bin/env bash
# Phase 6: Cloud Build Trigger を追加して自動化を有効にする
# GitHub への Push だけでパイプラインが自動実行されるようになる
#
# 前提: Cloud Build コンソールで GitHub リポジトリとの OAuth 接続が必要
#       Cloud Build → Triggers → Connect Repository
#
# 使い方:
#   export PROJECT_ID=<your-project>
#   export GITHUB_OWNER=<github-username>
#   export GITHUB_REPO=<repo-name>
#   bash scripts/phase6_trigger.sh
set -euo pipefail
# shellcheck source=scripts/common.sh
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

log "Phase 6: Cloud Build Trigger を設定"
check_project_id

[[ -n "$GITHUB_OWNER" ]] || err "GITHUB_OWNER が未設定です (export GITHUB_OWNER=<username>)"
[[ -n "$GITHUB_REPO"  ]] || err "GITHUB_REPO が未設定です (export GITHUB_REPO=<repo>)"

pushd "${PROJECT_ROOT}/terraform" > /dev/null

terraform apply \
  -auto-approve \
  -input=false \
  -var="project_id=${PROJECT_ID}" \
  -var="region=${REGION}"         \
  -var="github_owner=${GITHUB_OWNER}" \
  -var="github_repo=${GITHUB_REPO}"   \
  -var="github_branch=${GITHUB_BRANCH}"

popd > /dev/null

ok "Cloud Build Trigger を作成しました"
echo ""
echo "  これで pipeline/config.yaml を変更して git push するだけで"
echo "  パイプラインが自動実行されます。"
echo ""
echo "  体験フロー:"
echo "    1. pipeline/config.yaml の epochs を 5 → 10 に変更"
echo "    2. git commit -m 'increase epochs' && git push"
echo "    3. Cloud Build で自動実行を確認: https://console.cloud.google.com/cloud-build/builds"
echo "    4. Pipeline 完了後に Endpoint が自動更新される"
