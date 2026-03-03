#!/usr/bin/env bash
# 各フェーズスクリプトから source して使う共通設定

# ── 変数 ─────────────────────────────────────────────────────
PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${REGION:-asia-northeast1}"
GITHUB_OWNER="${GITHUB_OWNER:-}"
GITHUB_REPO="${GITHUB_REPO:-}"
GITHUB_BRANCH="${GITHUB_BRANCH:-main}"

DATA_BUCKET="${PROJECT_ID}-mlops-data"
SERVING_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/mlops/vtuber-predictor:latest"

# このファイルの場所から scripts/ → プロジェクトルートを解決
SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPTS_DIR}/.." && pwd)"

# ── ユーティリティ ────────────────────────────────────────────
log()  { echo ""; echo "▶ $*"; }
ok()   { echo "  ✅ $*"; }
warn() { echo "  ⚠️  $*"; }
err()  { echo ""; echo "❌ ERROR: $*" >&2; exit 1; }

check_project_id() {
  [[ -n "$PROJECT_ID" ]] || err "PROJECT_ID が未設定です (export PROJECT_ID=<your-project>)"
}

# Vertex AI Endpoint ID を terraform output から取得
get_endpoint_id() {
  pushd "${PROJECT_ROOT}/terraform" > /dev/null
  terraform output -raw endpoint_id
  popd > /dev/null
}

# Python 仮想環境が存在すれば activate
activate_venv() {
  if [[ -f "${PROJECT_ROOT}/.venv/bin/activate" ]]; then
    # shellcheck disable=SC1091
    source "${PROJECT_ROOT}/.venv/bin/activate"
  else
    warn ".venv が見つかりません。setup.sh を先に実行するか pip で依存パッケージをインストールしてください"
  fi
}
