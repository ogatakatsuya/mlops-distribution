#!/usr/bin/env bash
# Phase 0: Terraform でインフラを構築する
#
# 使い方:
#   export PROJECT_ID=<your-project>
#   bash scripts/phase0_terraform.sh
set -euo pipefail
# shellcheck source=scripts/common.sh
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

log "Phase 0-A: Terraform (インフラ構築)"
check_project_id

pushd "${PROJECT_ROOT}/terraform" > /dev/null

terraform init -upgrade -input=false -reconfigure

TF_ARGS=(
  -auto-approve
  -input=false
  -var="project_id=${PROJECT_ID}"
  -var="region=${REGION}"
  -var="github_branch=${GITHUB_BRANCH}"
)

if [[ -n "$GITHUB_OWNER" && -n "$GITHUB_REPO" ]]; then
  TF_ARGS+=(
    -var="github_owner=${GITHUB_OWNER}"
    -var="github_repo=${GITHUB_REPO}"
  )
  ok "Cloud Build Trigger を作成します (${GITHUB_OWNER}/${GITHUB_REPO})"
else
  warn "GITHUB_OWNER / GITHUB_REPO 未設定 → Cloud Build Trigger はスキップ"
  warn "Phase 6 を体験する場合は phase6_trigger.sh を実行してください"
fi

terraform apply "${TF_ARGS[@]}"

ok "インフラ構築完了"
ok "Endpoint ID: $(terraform output -raw endpoint_id)"

popd > /dev/null
