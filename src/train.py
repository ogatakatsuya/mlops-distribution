"""
Vertex AI Custom Training Job 用 YOLO 学習スクリプト。

Vertex AI が注入する環境変数:
  AIP_MODEL_DIR   : 学習済みモデルの出力先 GCS URI (例: gs://bucket/models/build-id)

Cloud Build / submit_job.py が設定する環境変数:
  DATA_BUCKET     : データセット・モデル保存用 GCS バケット名 (必須)
  DATASET_VERSION : データセットバージョン (デフォルト: v1)
  EPOCHS          : 学習エポック数 (デフォルト: 5)
  BATCH           : バッチサイズ (デフォルト: 16)
  IMGSZ           : 入力画像サイズ (デフォルト: 640)
  MODEL           : ベースモデル名 (デフォルト: yolov8n.pt)
  BUILD_ID        : Cloud Build ビルド ID (W&B ラン名に使用)
  WANDB_API_KEY   : W&B API キー (省略可)
  WANDB_PROJECT   : W&B プロジェクト名 (デフォルト: vtuber-detector)
"""
import os
import sys
import yaml
from pathlib import Path

from google.cloud import storage
from ultralytics import YOLO

# ── 環境変数 ──────────────────────────────────────────────────────────────
DATA_BUCKET     = os.environ["DATA_BUCKET"]
DATASET_VERSION = os.environ.get("DATASET_VERSION", "v1")
AIP_MODEL_DIR   = os.environ["AIP_MODEL_DIR"]   # Vertex AI が自動設定
EPOCHS          = int(os.environ.get("EPOCHS", "5"))
BATCH           = int(os.environ.get("BATCH", "16"))
IMGSZ           = int(os.environ.get("IMGSZ", "640"))
MODEL           = os.environ.get("MODEL", "yolov8n.pt")
BUILD_ID        = os.environ.get("BUILD_ID", "local")
WANDB_API_KEY   = os.environ.get("WANDB_API_KEY", "")
WANDB_PROJECT   = os.environ.get("WANDB_PROJECT", "vtuber-detector")

LOCAL_DATASET = Path("/tmp/dataset")
RUNS_DIR      = Path("/tmp/runs")


# ── 1. GCS からデータセットをダウンロード ────────────────────────────────
print(f"[1/3] Downloading dataset: gs://{DATA_BUCKET}/datasets/{DATASET_VERSION}/")
LOCAL_DATASET.mkdir(parents=True, exist_ok=True)

gcs = storage.Client()
bucket = gcs.bucket(DATA_BUCKET)
prefix = f"datasets/{DATASET_VERSION}/"
blobs = list(bucket.list_blobs(prefix=prefix))

if not blobs:
    print(f"ERROR: gs://{DATA_BUCKET}/{prefix} にファイルが見つかりません", file=sys.stderr)
    sys.exit(1)

for blob in blobs:
    relative = blob.name[len(prefix):]
    if not relative:
        continue
    dest = LOCAL_DATASET / relative
    dest.parent.mkdir(parents=True, exist_ok=True)
    blob.download_to_filename(str(dest))
    print(f"  {blob.name}")

# data.yaml の path キーを絶対パスに書き換え (ultralytics が相対解釈するため)
data_yaml_path = LOCAL_DATASET / "data.yaml"
with open(data_yaml_path) as f:
    data_cfg = yaml.safe_load(f)
data_cfg["path"] = str(LOCAL_DATASET)
with open(data_yaml_path, "w") as f:
    yaml.dump(data_cfg, f)


# ── 2. W&B セットアップ ────────────────────────────────────────────────────
if WANDB_API_KEY:
    import wandb
    from ultralytics.utils import SETTINGS
    wandb.login(key=WANDB_API_KEY)
    SETTINGS.update({"wandb": True})
    print(f"[W&B] enabled, project={WANDB_PROJECT} run={BUILD_ID}")
else:
    print("[W&B] WANDB_API_KEY 未設定 - W&B ログをスキップ")

# ── 3. YOLO 学習 ──────────────────────────────────────────────────────────
print(f"[2/3] Training {MODEL} for {EPOCHS} epochs (batch={BATCH}, imgsz={IMGSZ})")
model = YOLO(MODEL)
model.train(
    data=str(data_yaml_path),
    epochs=EPOCHS,
    batch=BATCH,
    imgsz=IMGSZ,
    project=WANDB_PROJECT if WANDB_API_KEY else str(RUNS_DIR),
    name=BUILD_ID,
    exist_ok=True,
)


# ── 4. best.pt を AIP_MODEL_DIR (GCS) にアップロード ─────────────────────
best_pt = RUNS_DIR / BUILD_ID / "weights" / "best.pt"
if not best_pt.exists():
    # W&B なしの場合は project=RUNS_DIR/train
    best_pt = RUNS_DIR / "train" / "weights" / "best.pt"
if not best_pt.exists():
    print("ERROR: best.pt が見つかりません。学習が失敗した可能性があります。", file=sys.stderr)
    sys.exit(1)

gcs_uri    = AIP_MODEL_DIR.rstrip("/")
after_gs   = gcs_uri[len("gs://"):]
bucket_name, _, blob_prefix = after_gs.partition("/")
blob_path  = f"{blob_prefix}/best.pt" if blob_prefix else "best.pt"

print(f"[3/3] Uploading best.pt → {gcs_uri}/best.pt")
gcs.bucket(bucket_name).blob(blob_path).upload_from_filename(str(best_pt))
print("Training complete!")
