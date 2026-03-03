"""
Vertex AI Custom Training Job 上で実行される学習スクリプト。
- GCS からデータセットをダウンロード
- YOLO26n で転移学習
- Vertex AI Experiments にメトリクスを記録
- 学習済みモデルを GCS へアップロード
"""
import argparse
import json
import os
import shutil
import tempfile
from pathlib import Path

import yaml
from google.cloud import aiplatform, storage
from ultralytics import YOLO

# ─────────────────────────────
# 引数
# ─────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--project_id",     type=str, required=True)
parser.add_argument("--region",         type=str, default="asia-northeast1")
parser.add_argument("--data_bucket",    type=str, default="")
parser.add_argument("--data_version",   type=str, default="v1")
parser.add_argument("--experiment",     type=str, default="yolo26-vtuber")
parser.add_argument("--run_name",       type=str, required=True)  # 例: "epochs10-lr001"
parser.add_argument("--epochs",         type=int, default=10)
parser.add_argument("--lr0",            type=float, default=0.01)
parser.add_argument("--freeze",         type=int, default=10)
parser.add_argument("--imgsz",          type=int, default=640)
parser.add_argument("--patience",       type=int, default=10)
# ローカルデータを使う場合は --local_data_dir を指定（GCSダウンロードをスキップ）
parser.add_argument("--local_data_dir", type=str, default="")
args = parser.parse_args()

LOCAL_DATA_DIR = Path(args.local_data_dir) if args.local_data_dir else Path("/tmp/dataset")
LOCAL_RUN_DIR  = Path("/tmp/runs/train")

# ─────────────────────────────
# 1. Vertex AI Experiments 初期化
# ─────────────────────────────
aiplatform.init(
    project=args.project_id,
    location=args.region,
    experiment=args.experiment,
)

with aiplatform.start_run(run=args.run_name, resume=True):

    aiplatform.log_params({
        "epochs":       args.epochs,
        "lr0":          args.lr0,
        "freeze":       args.freeze,
        "imgsz":        args.imgsz,
        "patience":     args.patience,
        "data_version": args.data_version,
        "model":        "yolo26n",
    })

    # ─────────────────────────────
    # 2. データセット準備
    # ─────────────────────────────
    if args.local_data_dir:
        # ローカル動作確認モード: GCS ダウンロードをスキップ
        print(f"Using local dataset: {LOCAL_DATA_DIR}")
    else:
        # クラウド実行モード: GCS からダウンロード
        print(f"Downloading dataset {args.data_version} from GCS...")
        gcs = storage.Client(project=args.project_id)
        bucket = gcs.bucket(args.data_bucket)

        LOCAL_DATA_DIR.mkdir(parents=True, exist_ok=True)
        blobs = bucket.list_blobs(prefix=f"datasets/{args.data_version}/")
        for blob in blobs:
            relative = blob.name.replace(f"datasets/{args.data_version}/", "")
            if not relative:
                continue
            local_path = LOCAL_DATA_DIR / relative
            local_path.parent.mkdir(parents=True, exist_ok=True)
            blob.download_to_filename(str(local_path))

        print(f"Dataset downloaded to {LOCAL_DATA_DIR}")

    # ─────────────────────────────
    # 3. YOLO26n 転移学習
    # ─────────────────────────────
    # data.yaml の path を実行環境の絶対パスに書き換えた一時ファイルを作成
    # （data.yaml の path: /tmp/dataset はクラウド用のため、ローカルでは上書きが必要）
    src_yaml = LOCAL_DATA_DIR / "data.yaml"
    data_cfg = yaml.safe_load(src_yaml.read_text())
    data_cfg["path"] = str(LOCAL_DATA_DIR.resolve())
    tmp_yaml = tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w")
    yaml.dump(data_cfg, tmp_yaml)
    tmp_yaml.flush()

    print("Starting YOLO26n training...")
    model = YOLO("yolo26n.pt")

    results = model.train(
        data=tmp_yaml.name,
        epochs=args.epochs,
        lr0=args.lr0,
        freeze=args.freeze,
        imgsz=args.imgsz,
        patience=args.patience,
        augment=True,
        project="/tmp/runs",
        name="train",
        exist_ok=True,
    )

    # ─────────────────────────────
    # 4. メトリクスを Vertex AI Experiments へ記録
    # ─────────────────────────────
    metrics = results.results_dict
    aiplatform.log_metrics({
        "mAP50":    metrics.get("metrics/mAP50(B)", 0),
        "mAP50-95": metrics.get("metrics/mAP50-95(B)", 0),
        "precision": metrics.get("metrics/precision(B)", 0),
        "recall":    metrics.get("metrics/recall(B)", 0),
    })
    print(f"mAP50: {metrics.get('metrics/mAP50(B)', 0):.4f}")

    # ─────────────────────────────
    # 5. best.pt を GCS へアップロード
    # ─────────────────────────────
    best_pt = LOCAL_RUN_DIR / "weights" / "best.pt"

    if args.local_data_dir:
        # ローカル動作確認モード: GCS アップロードをスキップ
        print(f"[LOCAL MODE] Model saved at: {best_pt}")
    else:
        gcs_model_path = f"models/{args.run_name}/best.pt"
        bucket.blob(gcs_model_path).upload_from_filename(str(best_pt))
        print(f"Model uploaded to gs://{args.data_bucket}/{gcs_model_path}")

        # metrics.json を GCS へ保存（パイプラインの evaluate ステップが参照する）
        metrics_data = {
            "mAP50":     metrics.get("metrics/mAP50(B)", 0),
            "mAP50-95":  metrics.get("metrics/mAP50-95(B)", 0),
            "precision": metrics.get("metrics/precision(B)", 0),
            "recall":    metrics.get("metrics/recall(B)", 0),
        }
        metrics_path = f"models/{args.run_name}/metrics.json"
        bucket.blob(metrics_path).upload_from_string(json.dumps(metrics_data, indent=2))
        print(f"Metrics saved to gs://{args.data_bucket}/{metrics_path}")

print("Training complete!")
