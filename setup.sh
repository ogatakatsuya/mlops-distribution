#!/usr/bin/env bash
# ==============================================================
#  MLOps ハンズオン セットアップスクリプト
#  terraform apply → データ準備 → 推論コンテナビルド →
#  実験ジョブ投入 → パイプライン初回実行 まで一括自動化
#
#  使い方:
#    export PROJECT_ID=<your-project-id>
#    export GITHUB_OWNER=<github-username>   # Phase 6 自動化が不要なら省略可
#    export GITHUB_REPO=<repo-name>          # 同上
#    bash setup.sh
# ==============================================================
set -euo pipefail

# ── 設定 ──────────────────────────────────────────────────────
PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${REGION:-asia-northeast1}"
GITHUB_OWNER="${GITHUB_OWNER:-}"
GITHUB_REPO="${GITHUB_REPO:-}"
GITHUB_BRANCH="${GITHUB_BRANCH:-main}"

DATA_BUCKET="${PROJECT_ID}-mlops-data"
SERVING_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/mlops/vtuber-predictor:latest"

# terraform apply 後に設定される
ENDPOINT_ID=""

# スクリプトが置かれているディレクトリを起点にする
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── ユーティリティ ───────────────────────────────────────────
log()  { echo ""; echo "▶ $*"; }
ok()   { echo "  ✅ $*"; }
warn() { echo "  ⚠️  $*"; }
err()  { echo ""; echo "❌ ERROR: $*" >&2; exit 1; }

# ── 前提チェック ──────────────────────────────────────────────
check_prerequisites() {
  log "前提チェック"

  [[ -n "$PROJECT_ID" ]] || err "PROJECT_ID が未設定です (export PROJECT_ID=<your-project>)"

  for cmd in gcloud terraform docker python3 gsutil; do
    command -v "$cmd" &>/dev/null || err "$cmd が見つかりません。インストールしてください。"
  done

  if [[ -z "$GITHUB_OWNER" || -z "$GITHUB_REPO" ]]; then
    warn "GITHUB_OWNER / GITHUB_REPO 未設定 → Cloud Build Trigger はスキップされます"
    warn "Phase 6 (config.yaml 変更で自動実行) を体験する場合は事前に設定してください"
  fi

  ok "チェック完了 (PROJECT_ID=${PROJECT_ID}, REGION=${REGION})"
}

# ── Phase 0: Terraform ──────────────────────────────────────
phase0_terraform() {
  log "Phase 0: Terraform でインフラを構築"

  pushd terraform > /dev/null
  terraform init -upgrade -input=false -reconfigure

  TF_ARGS=(
    -auto-approve
    -input=false
    -var="project_id=${PROJECT_ID}"
    -var="region=${REGION}"
    -var="github_branch=${GITHUB_BRANCH}"
  )

  # GitHub 情報が揃っている場合のみ Cloud Build Trigger を作成
  if [[ -n "$GITHUB_OWNER" && -n "$GITHUB_REPO" ]]; then
    TF_ARGS+=(
      -var="github_owner=${GITHUB_OWNER}"
      -var="github_repo=${GITHUB_REPO}"
    )
    ok "Cloud Build Trigger を作成します (${GITHUB_OWNER}/${GITHUB_REPO})"
  fi

  terraform apply "${TF_ARGS[@]}"

  ENDPOINT_ID="$(terraform output -raw endpoint_id)"
  ok "インフラ構築完了"
  ok "Endpoint ID: ${ENDPOINT_ID}"

  popd > /dev/null
}

# ── Phase 1: データセットを GCS へアップロード ───────────────
phase1_upload_dataset() {
  log "Phase 1: データセットを GCS へアップロード"

  [[ -d vtuber_dataset ]] || err "vtuber_dataset/ ディレクトリが見つかりません"

  # rsync で差分のみアップロード（冪等）
  gsutil -m rsync -r -d vtuber_dataset/ "gs://${DATA_BUCKET}/datasets/v1/"
  ok "gs://${DATA_BUCKET}/datasets/v1/ へアップロード完了"
}

# ── 推論コンテナをビルド & プッシュ ──────────────────────────
build_serving_container() {
  log "Serving Container: ビルド & Artifact Registry へプッシュ"

  gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet

  # Apple Silicon (M1/M2/M3) でも Vertex AI (x86) で動くよう --platform 指定
  docker build --platform linux/amd64 -t "$SERVING_IMAGE" serve/
  docker push "$SERVING_IMAGE"

  ok "Pushed: ${SERVING_IMAGE}"
}

# ── Python 仮想環境セットアップ ──────────────────────────────
setup_python() {
  log "Python 仮想環境セットアップ"

  if [[ ! -d .venv ]]; then
    python3 -m venv .venv
  fi

  # shellcheck disable=SC1091
  source .venv/bin/activate

  pip install -q \
    -r src/requirements.txt \
    "kfp>=2.0" \
    "google-cloud-pipeline-components>=2.0"

  ok "依存パッケージインストール完了"
}

# ── Phase 2: Vertex AI Experiments（学習ジョブ投入）──────────
phase2_experiments() {
  log "Phase 2: Custom Training Job を投入 (epochs=3, epochs=5)"
  echo "     非同期投入のため即座に次のフェーズへ進みます"
  echo "     進捗: https://console.cloud.google.com/vertex-ai/training/custom-jobs"

  export PROJECT_ID REGION
  python src/submit_job.py

  ok "2 件のジョブを投入しました (epochs=3 / epochs=5)"
}

# ── Phase 5: パイプライン初回実行 ────────────────────────────
phase5_pipeline() {
  log "Phase 5: Vertex AI Pipeline を初回実行"

  # train.py を GCS へ配置（パイプライン内の学習コンポーネントが参照）
  gsutil cp src/train.py "gs://${DATA_BUCKET}/scripts/train.py"
  ok "src/train.py → gs://${DATA_BUCKET}/scripts/train.py"

  python pipeline/definition.py \
    --project_id="${PROJECT_ID}" \
    --region="${REGION}"        \
    --endpoint_id="${ENDPOINT_ID}"

  ok "パイプラインを投入しました"
  echo "     進捗: https://console.cloud.google.com/vertex-ai/pipelines"
}

# ── メイン ──────────────────────────────────────────────────
main() {
  echo "=============================================="
  echo "  MLOps ハンズオン セットアップ"
  echo "=============================================="

  check_prerequisites
  phase0_terraform
  phase1_upload_dataset
  build_serving_container
  setup_python
  phase2_experiments
  phase5_pipeline

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
  if [[ -n "$GITHUB_OWNER" && -n "$GITHUB_REPO" ]]; then
    echo "  Phase 6 (自動化) の体験:"
    echo "    pipeline/config.yaml を変更して git push するだけで"
    echo "    パイプラインが自動実行されます"
  else
    echo "  Phase 6 (自動化) を体験する場合:"
    echo "    export GITHUB_OWNER=<username> GITHUB_REPO=<repo>"
    echo "    bash setup.sh  # 再実行で Cloud Build Trigger が追加されます"
  fi
  echo ""
}

main "$@"
