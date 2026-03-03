# MLOps ハンズオン — VTuber キャラクター検出パイプライン

**「`config.yaml` を変えて Push するだけで、本番の AI が自動更新される」** 体験を Google Cloud で学ぶハンズオンです。

YOLO26n を使ってオリジナルの VTuber キャラクター検出モデルを作り、
Vertex AI Pipelines による自動学習・評価・デプロイまでを構築します。

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
[Cloud Build Trigger]          ← Phase 6 で自動化
        │
        ▼
[Vertex AI Pipelines]
  Step 1: データセット確認 (GCS)
  Step 2: YOLO26n 転移学習 (GPU Custom Training Job)
  Step 3: mAP50 評価・閾値チェック
        │ 閾値超過のみ
  Step 4: Vertex AI Model Registry に登録
  Step 5: Vertex AI Endpoint へ自動デプロイ
        │
        ▼
[Vertex AI Endpoint] ← モデルが変わっても Endpoint ID は不変
        │
        ▼
  ローカルアプリから推論リクエスト
```

---

## 使用技術スタック

| 役割 | 技術 |
|---|---|
| インフラ管理 | Terraform + Google Cloud |
| データ・モデル管理 | Cloud Storage (GCS) |
| 実験管理 | Vertex AI Experiments |
| 学習モデル | YOLO26n (Ultralytics) |
| パイプライン | Vertex AI Pipelines (KFP v2) |
| CI/CD トリガー | Cloud Build |
| 推論エンドポイント | Vertex AI Endpoint |
| 推論サーバー | FastAPI (serve/) |

---

## 前提条件

| ツール | 確認コマンド |
|---|---|
| Google Cloud SDK | `gcloud --version` |
| Terraform >= 1.5 | `terraform --version` |
| Docker | `docker --version` |
| Python >= 3.11 | `python3 --version` |

```bash
# GCP 認証
gcloud auth login
gcloud auth application-default login
```

---

## フェーズ構成

```
Phase 0: 環境準備（Terraform + 推論コンテナビルド）
Phase 1: データセット管理（GCS アップロード）
Phase 2: 実験管理（Vertex AI Experiments で比較）
Phase 5: パイプライン化（Vertex AI Pipelines）
Phase 6: 自動化（Cloud Build Trigger）
```

> Phase 3（Model Registry 登録）と Phase 4（Endpoint デプロイ）は
> Phase 5 のパイプライン内ステップとして実装されています。

---

### Phase 0-A: インフラ構築（Terraform）

GCS・Artifact Registry・Vertex AI Endpoint・IAM を作成します。

```bash
export PROJECT_ID=<your-gcp-project-id>
bash scripts/phase0_terraform.sh
```

**作成されるリソース:**
- GCS バケット: `{PROJECT_ID}-mlops-data`（データ・モデル用）
- GCS バケット: `{PROJECT_ID}-mlops-pipeline`（パイプラインルート用）
- Artifact Registry: `{REGION}-docker.pkg.dev/{PROJECT_ID}/mlops`
- Vertex AI Endpoint: `vtuber-detector`（IDを固定）
- IAM サービスアカウント: `mlops-vertex-ai`, `mlops-cloud-build`

---

### Phase 0-B: 推論コンテナのビルド & プッシュ

Vertex AI Endpoint で使う YOLO 推論サーバーを Artifact Registry へ登録します。
モデルが更新されても推論ロジックが変わらない限り、**再実行不要**です。

```bash
bash scripts/phase0_serving.sh
```

---

### Phase 1: データセットを GCS へアップロード

ローカルの `vtuber_dataset/` を GCS に同期します（差分のみ転送）。

```bash
bash scripts/phase1_dataset.sh
```

**GCS のデータ構造:**
```
gs://{PROJECT_ID}-mlops-data/
└── datasets/
    └── v1/
        ├── train/images/
        ├── train/labels/
        ├── valid/images/
        ├── valid/labels/
        └── data.yaml
```

> データを追加したら `v2/` として同じ構造でアップロードし、
> `pipeline/config.yaml` の `data_version: v2` に変更してください。

---

### Phase 2: 実験管理（Vertex AI Experiments）

ハイパーパラメータを変えた 2 つの学習ジョブを投入して精度を比較します。

```bash
bash scripts/phase2_experiments.sh
```

**投入されるジョブ:**
| ジョブ名 | epochs | lr0 |
|---|---|---|
| `epochs3-lr001` | 3 | 0.01 |
| `epochs5-lr001` | 5 | 0.01 |

**結果の確認:**
[Vertex AI → Experiments](https://console.cloud.google.com/vertex-ai/experiments) で
各ジョブの `mAP50` を比較できます。

---

### Phase 5: パイプライン化（Vertex AI Pipelines）

学習 → 評価 → 登録 → デプロイの全ステップを自動実行します。
`map_threshold` を超えた場合のみ Endpoint が更新されます。

```bash
bash scripts/phase5_pipeline.sh
```

**パイプラインのステップ:**

```
validate_data → train_model → check_accuracy → register_model → deploy_model
                                     │
                              mAP50 < 閾値なら
                              ここで終了（デプロイしない）
```

**設定ファイル:** `pipeline/config.yaml`

```yaml
data_version: v1    # 使用するデータセットバージョン
epochs: 5           # 学習エポック数
lr0: 0.01           # 初期学習率
freeze: 10          # バックボーン固定レイヤー数
map_threshold: 0.3  # この mAP50 を超えた場合のみデプロイ
```

---

### Phase 6: 自動化（Cloud Build Trigger）

`pipeline/config.yaml` を変更して Push するだけでパイプラインが自動実行されます。

**事前準備:** GCP コンソールで GitHub リポジトリを接続してください
> Cloud Build → Triggers → [Connect Repository](https://console.cloud.google.com/cloud-build/triggers)

```bash
export GITHUB_OWNER=<your-github-username>
export GITHUB_REPO=<your-repo-name>
bash scripts/phase6_trigger.sh
```

**体験フロー:**
```bash
# 1. config.yaml を変更
vim pipeline/config.yaml   # epochs: 5 → 10 に変更

# 2. Push するだけでパイプラインが自動実行
git add pipeline/config.yaml
git commit -m "increase epochs to 10"
git push

# 3. Cloud Build で自動実行を確認
# https://console.cloud.google.com/cloud-build/builds

# 4. Vertex AI Pipelines で進捗を確認
# https://console.cloud.google.com/vertex-ai/pipelines

# 5. 精度が閾値を超えると Endpoint が自動更新される
# アプリのコードは一切触っていないのに検出精度が向上している
```

---

## リポジトリ構成

```
.
├── setup.sh                 # 全フェーズ一括実行
├── cloudbuild.yaml          # Cloud Build 設定
├── pipeline/
│   ├── config.yaml          # ← 受講者が変更するファイル
│   ├── definition.py        # KFP パイプライン定義
│   └── components/
│       ├── download_data.py # Step 1: データ確認
│       ├── train.py         # Step 2: YOLO26n 学習
│       ├── evaluate.py      # Step 3: mAP 評価
│       ├── register.py      # Step 4: Model Registry 登録
│       └── deploy.py        # Step 5: Endpoint デプロイ
├── scripts/
│   ├── common.sh            # 共通関数・変数
│   ├── phase0_terraform.sh
│   ├── phase0_serving.sh
│   ├── phase1_dataset.sh
│   ├── phase2_experiments.sh
│   ├── phase5_pipeline.sh
│   └── phase6_trigger.sh
├── serve/
│   ├── app.py               # FastAPI 推論サーバー
│   ├── Dockerfile
│   └── requirements.txt
├── src/
│   ├── train.py             # Custom Training Job スクリプト
│   ├── submit_job.py        # Phase 2 用ジョブ投入スクリプト
│   └── requirements.txt
├── terraform/               # インフラ定義（一度だけ実行）
└── preprocess/              # データセット作成ツール（参考）
    ├── distill.py           # GroundingDINO による自動ラベリング
    ├── frame.py             # 動画からフレーム抽出
    └── download.py          # 動画ダウンロード
```

---

## データセットの作り方（参考）

`vtuber_dataset/` は以下の手順で作成しました。自分のキャラクターで試す場合に参考にしてください。

```bash
cd preprocess

# 1. VTuber の配信動画をダウンロード
python download.py

# 2. 動画からフレームを抽出
python frame.py

# 3. GroundingDINO で自動ラベリング → YOLO 形式データセットを生成
python distill.py
```

---

## GCP コンソール確認リンク

| 項目 | URL |
|---|---|
| Vertex AI Experiments | https://console.cloud.google.com/vertex-ai/experiments |
| Vertex AI Pipelines | https://console.cloud.google.com/vertex-ai/pipelines |
| Vertex AI Model Registry | https://console.cloud.google.com/vertex-ai/models |
| Vertex AI Endpoints | https://console.cloud.google.com/vertex-ai/endpoints |
| Cloud Build 履歴 | https://console.cloud.google.com/cloud-build/builds |
| GCS バケット | https://console.cloud.google.com/storage/browser |
