#!/usr/bin/env bash
# ==============================================================
#  MLOps ハンズオン セットアップ（全フェーズ一括実行）
#
#  使い方:
#    export PROJECT_ID=<your-project-id>
#    export GITHUB_OWNER=<github-username>   # Phase 6 不要なら省略可
#    export GITHUB_REPO=<repo-name>          # 同上
#    bash setup.sh
#
#  各フェーズを個別に実行したい場合:
#    bash scripts/phase0_terraform.sh
#    bash scripts/phase0_serving.sh
#    bash scripts/phase1_dataset.sh
#    bash scripts/phase2_experiments.sh
#    bash scripts/phase5_pipeline.sh
#    bash scripts/phase6_trigger.sh   # GitHub 設定後に実行
# ==============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS="${SCRIPT_DIR}/scripts"

# ── 前提チェック ──────────────────────────────────────────────
check_prerequisites() {
  echo ""
  echo "▶ 前提チェック"

  local missing=0
  for cmd in gcloud terraform docker python3 gsutil; do
    if ! command -v "$cmd" &>/dev/null; then
      echo "  ❌ $cmd が見つかりません"
      missing=1
    fi
  done
  [[ $missing -eq 0 ]] || { echo "上記のツールをインストールしてください" >&2; exit 1; }

  local project_id="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
  [[ -n "$project_id" ]] || { echo "  ❌ PROJECT_ID が未設定です (export PROJECT_ID=<your-project>)" >&2; exit 1; }

  echo "  ✅ OK (PROJECT_ID=${project_id}, REGION=${REGION:-asia-northeast1})"
}

# ── Python 仮想環境セットアップ ──────────────────────────────
setup_python() {
  echo ""
  echo "▶ Python 仮想環境セットアップ"

  if [[ ! -d "${SCRIPT_DIR}/.venv" ]]; then
    python3 -m venv "${SCRIPT_DIR}/.venv"
  fi

  # pip で直接インストール（subshell から activate 不要）
  "${SCRIPT_DIR}/.venv/bin/pip" install -q \
    -r "${SCRIPT_DIR}/src/requirements.txt" \
    "kfp>=2.0"

  echo "  ✅ 依存パッケージインストール完了"
}

# ── メイン ────────────────────────────────────────────────────
echo "=============================================="
echo "  MLOps ハンズオン セットアップ"
echo "=============================================="

check_prerequisites

bash "${SCRIPTS}/phase0_terraform.sh"
bash "${SCRIPTS}/phase0_serving.sh"
bash "${SCRIPTS}/phase1_dataset.sh"
setup_python
bash "${SCRIPTS}/phase2_experiments.sh"
bash "${SCRIPTS}/phase5_pipeline.sh"

echo ""
echo "=============================================="
echo "  セットアップ完了！"
echo "=============================================="
echo ""
echo "  確認リンク:"
echo "    Experiments : https://console.cloud.google.com/vertex-ai/experiments"
echo "    Pipelines   : https://console.cloud.google.com/vertex-ai/pipelines"
echo "    Endpoint    : https://console.cloud.google.com/vertex-ai/endpoints"
echo ""

GITHUB_OWNER="${GITHUB_OWNER:-}"
GITHUB_REPO="${GITHUB_REPO:-}"
if [[ -n "$GITHUB_OWNER" && -n "$GITHUB_REPO" ]]; then
  echo "  Phase 6: pipeline/config.yaml を変更して git push するだけで"
  echo "           パイプラインが自動実行されます"
else
  echo "  Phase 6 (自動化) を体験する場合:"
  echo "    export GITHUB_OWNER=<username> GITHUB_REPO=<repo>"
  echo "    bash scripts/phase6_trigger.sh"
fi
echo ""
