#!/usr/bin/env bash
# Phase 0: Terraform でインフラを構築する
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/terraform"

PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${REGION:-asia-northeast1}"

if [ -z "$PROJECT_ID" ]; then
  echo "ERROR: PROJECT_ID が未設定です"
  exit 1
fi

echo "=== Phase 0: Terraform Apply ==="
echo "  Project : $PROJECT_ID"
echo "  Region  : $REGION"
echo ""

TF_ARGS=(
  -auto-approve
  -input=false
  -var="project_id=${PROJECT_ID}"
  -var="region=${REGION}"
)

if [[ -n "${GITHUB_OWNER:-}" && -n "${GITHUB_REPO:-}" ]]; then
  TF_ARGS+=(
    -var="github_owner=${GITHUB_OWNER}"
    -var="github_repo=${GITHUB_REPO}"
    -var="github_branch=${GITHUB_BRANCH:-main}"
  )
  echo "  GitHub  : ${GITHUB_OWNER}/${GITHUB_REPO} (Cloud Build Trigger を作成)"
else
  echo "  GitHub  : 未設定 (Cloud Build Trigger はスキップ)"
fi

terraform init -upgrade -input=false
terraform apply "${TF_ARGS[@]}"

echo ""
echo "=== 完了 ==="
echo "  Serving URL: $(terraform output -raw serving_url 2>/dev/null || echo '(未設定)')"
