# MLOps ハンズオン — VTuber キャラクター検出パイプライン

**「`config.yaml` を変えて Push するだけで、本番の AI が自動更新される」** 体験を Google Cloud で学ぶハンズオンです。

YOLO26n を使ってオリジナルの VTuber キャラクター検出モデルを作り、
Vertex AI Pipelines による自動学習・デプロイまでを構築します。

---

## 検出対象キャラクター

| クラス名 | キャラクター |
|---|---|
| `debidebi` | でびでびでびる |
| `runrun` | ルンルン |

---

## 全体アーキテクチャ

```
pipeline/config.yaml を変更して git push
        │
        ▼
[Cloud Build Trigger]
  ├─ trainer イメージをビルド & push  ┐ 並列
  └─ serving イメージをビルド & push  ┘
        │
        ▼
[Vertex AI Pipelines] ← Cloud Build はここで即終了
  Step 1: YOLO26n 学習 (Custom Training Job)
  Step 2: Cloud Run サービスのモデルを更新
        │
        ▼
[Cloud Run] ← 起動時に GCS からモデルをダウンロード
        │
        ▼
  demo/ アプリから推論リクエスト
```

---

## 使用技術スタック

| 役割 | 技術 |
|---|---|
| インフラ管理 | Terraform + Google Cloud |
| データ・モデル管理 | Cloud Storage (GCS) |
| 自動ラベリング | Grounding DINO (autodistill) |
| 学習モデル | YOLO26n (Ultralytics) |
| 実験追跡 | Weights & Biases |
| パイプライン | Vertex AI Pipelines (KFP v2) |
| CI/CD | Cloud Build |
| 推論サーバー | FastAPI + Cloud Run |
| デモ UI | Streamlit |

---

## 前提条件

| ツール | 確認コマンド |
|---|---|
| Google Cloud SDK | `gcloud --version` |
| Terraform >= 1.5 | `terraform --version` |
| Docker | `docker --version` |
| Python >= 3.11 + uv | `uv --version` |

```bash
gcloud auth login
gcloud auth application-default login
```

---

## フェーズ構成

```
Phase 0: インフラ構築 (Terraform)
Phase 1: データセット GCS アップロード
Phase 5: パイプライン実行 (Cloud Build → Vertex AI)
Phase 6: Push 自動化 (Cloud Build Trigger)
```

---

### Phase 0: インフラ構築

```bash
cd terraform
terraform init
terraform apply
```

**作成されるリソース:**
- GCS バケット: `{PROJECT_ID}-mlops-data`（データ・モデル用）
- GCS バケット: `{PROJECT_ID}-mlops-pipeline`（パイプラインルート用）
- Artifact Registry: `{REGION}-docker.pkg.dev/{PROJECT_ID}/mlops`
- Cloud Run サービス: `vtuber-detector`（初回は placeholder）
- IAM サービスアカウント: `mlops-vertex-ai`, `mlops-cloud-build`

---

### データセットの作成

`vtuber_dataset/` は以下の手順で作成します。

```bash
cd preprocess

# 1. VTuber の配信動画からフレームを抽出
python frame.py

# 2. Grounding DINO でキャラクターごとに自動ラベリング
#    キャラクターごとに別オントロジーで実行し、混入を防ぐ
uv run python distill.py

# 3. ラベルのクリーンアップ（混入チェック）
#    debidebi フレームに runrun ボックスが入っている場合などを除去
uv run python fix_labels.py
```

**`distill.py` の注意点:**

`CHARACTERS` 辞書にキャラクターごとの Grounding DINO プロンプトを定義します。
**1 つのオントロジーに複数キャラを混ぜると検出が混入するため、必ずキャラクターを分けて実行してください。**

```python
CHARACTERS = {
    "debidebi": ("anime vtuber girl with cat ears and dark outfit", "debidebi"),
    "runrun":   ("anime vtuber girl with white bunny ears",         "runrun"),
}
```

**データセット構造（YOLO 形式）:**
```
vtuber_dataset/
├── data.yaml
├── train/
│   ├── images/   debidebi_frame_*.jpg, runrun_frame_*.jpg
│   └── labels/   同名の .txt（class_id cx cy w h）
└── valid/
    ├── images/
    └── labels/
```

**データセットビジュアライザー:**

ラベルが正しいか確認するための Streamlit アプリ。

```bash
cd demo
uv run streamlit run dataset_viewer.py
```

---

### Phase 1: データセットを GCS へアップロード

```bash
# v1 としてアップロード（デフォルト）
bash scripts/phase1_dataset.sh

# バージョンを指定する場合
DATASET_VERSION=v2 bash scripts/phase1_dataset.sh
```

`pipeline/config.yaml` の `dataset.version` を合わせて変更してください。

---

### Phase 5: パイプライン実行

Cloud Build でコンテナをビルドし、Vertex AI Pipelines へパイプラインを投入します。
Cloud Build はパイプライン submit 後に即終了し、学習・デプロイは Vertex AI が非同期で実行します。

```bash
# W&B でメトリクスを記録する場合
export WANDB_API_KEY=<your-wandb-api-key>

bash scripts/phase5_pipeline.sh
```

**設定ファイル:** `pipeline/config.yaml`

```yaml
model:
  architecture: yolo26n
  epochs: 100
  batch_size: 16
  image_size: 640

dataset:
  version: v2

training:
  machine_type: n1-highmem-4
```

**パイプラインの流れ:**

```
Cloud Build
  ├─ build-trainer  (src/)   ┐ 並列ビルド
  └─ build-serving  (serve/) ┘
        ↓ push 完了後
  submit-pipeline → 即終了

Vertex AI Pipelines（非同期）
  train_component  → yolo-train-{BUILD_ID} Custom Job を起動・完了待ち
  deploy_component → Cloud Run の AIP_STORAGE_URI を新モデルパスに更新
```

**進捗確認:**
- [Cloud Build](https://console.cloud.google.com/cloud-build/builds)
- [Vertex AI Pipelines](https://console.cloud.google.com/vertex-ai/pipelines)
- [Custom Training Jobs](https://console.cloud.google.com/vertex-ai/training/custom-jobs)

---

### Phase 6: 自動化（Push トリガー）

`pipeline/config.yaml` を変更して Push するだけでパイプラインが自動実行されます。

**事前準備:** GCP コンソールで GitHub リポジトリを接続してください
> Cloud Build → Triggers → [Connect Repository](https://console.cloud.google.com/cloud-build/triggers)

`terraform/variables.tf` に `github_owner` と `github_repo` を設定して `terraform apply` するとトリガーが作成されます。

```bash
# config.yaml を変更して push するだけ
vim pipeline/config.yaml
git add pipeline/config.yaml && git commit -m "update config" && git push
```

---

### デモアプリ

```bash
cd demo
uv run streamlit run app.py
```

サイドバーで **API モード** を選択し、エンドポイント URL を設定：

```
https://<CLOUD_RUN_URL>/predict
```

---

## リポジトリ構成

```
.
├── cloudbuild.yaml          # Cloud Build 設定
├── pipeline/
│   ├── config.yaml          # ← 変更してパイプラインを制御するファイル
│   ├── definition.py        # KFP パイプライン定義 (train → deploy)
│   └── submit.py            # パイプラインコンパイル & 投入スクリプト
├── scripts/
│   ├── phase0_terraform.sh
│   ├── phase1_dataset.sh
│   ├── phase5_pipeline.sh
│   └── phase6_trigger.sh
├── serve/
│   ├── app.py               # FastAPI 推論サーバー（起動時に GCS からモデルをロード）
│   ├── Dockerfile
│   └── requirements.txt
├── src/
│   ├── train.py             # Custom Training Job スクリプト（W&B 対応）
│   ├── Dockerfile
│   └── requirements.txt
├── demo/
│   ├── app.py               # Streamlit 推論デモ（Local / API モード）
│   └── dataset_viewer.py    # データセットビジュアライザー
├── preprocess/
│   ├── distill.py           # Grounding DINO による自動ラベリング
│   ├── fix_labels.py        # ラベル混入クリーンアップ
│   ├── frame.py             # 動画からフレーム抽出
│   └── download.py          # 動画ダウンロード
└── terraform/               # インフラ定義
```

---

## GCP コンソール確認リンク

| 項目 | URL |
|---|---|
| Cloud Build 履歴 | https://console.cloud.google.com/cloud-build/builds |
| Vertex AI Pipelines | https://console.cloud.google.com/vertex-ai/pipelines |
| Custom Training Jobs | https://console.cloud.google.com/vertex-ai/training/custom-jobs |
| Cloud Run | https://console.cloud.google.com/run |
| GCS バケット | https://console.cloud.google.com/storage/browser |
| Artifact Registry | https://console.cloud.google.com/artifacts |
