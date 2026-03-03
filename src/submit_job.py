"""
ローカルから Vertex AI Custom Training Job を投入するスクリプト。
複数の設定で実行して Vertex AI Experiments で結果を比較する。

使い方:
  export PROJECT_ID=mlops-489016
  python src/submit_job.py
"""
import os
from pathlib import Path

from google.cloud import aiplatform

PROJECT_ID  = os.environ["PROJECT_ID"]
REGION      = os.environ.get("REGION", "asia-northeast1")
DATA_BUCKET = f"{PROJECT_ID}-mlops-data"
VERTEX_AI_SA = f"mlops-vertex-ai@{PROJECT_ID}.iam.gserviceaccount.com"

# Vertex AI が提供する PyTorch + GPU のビルド済みコンテナ
TRAIN_CONTAINER = "us-docker.pkg.dev/vertex-ai/training/pytorch-gpu.2-2:latest"

aiplatform.init(
    project=PROJECT_ID,
    location=REGION,
    staging_bucket=f"gs://{DATA_BUCKET}",  # スクリプトの一時アップロード先
)


def submit(run_name: str, epochs: int, lr0: float, freeze: int = 10):
    """Custom Training Job を1件投入する"""
    display_name = f"yolo26-{run_name}"
    print(f"\nSubmitting job: {display_name}  (epochs={epochs}, lr0={lr0})")

    job = aiplatform.CustomTrainingJob(
        display_name=display_name,
        script_path=str(Path(__file__).parent / "train.py"),
        container_uri=TRAIN_CONTAINER,
        requirements=["ultralytics", "google-cloud-aiplatform", "google-cloud-storage"],
    )

    job.run(
        args=[
            f"--project_id={PROJECT_ID}",
            f"--region={REGION}",
            f"--data_bucket={DATA_BUCKET}",
            "--data_version=v1",
            "--experiment=yolo26-vtuber",
            f"--run_name={run_name}",
            f"--epochs={epochs}",
            f"--lr0={lr0}",
            f"--freeze={freeze}",
            "--imgsz=640",
            "--patience=10",
        ],
        machine_type="n1-standard-4",
        accelerator_type="NVIDIA_TESLA_T4",
        accelerator_count=1,
        service_account=VERTEX_AI_SA,
        sync=False,  # 非同期で投入（完了を待たない）
    )
    # sync=False のため job オブジェクトはまだ GCP 上に存在しない
    # display_name はローカル変数から参照する
    print(f"Job submitted: {display_name}")
    return job


if __name__ == "__main__":
    submit(run_name="epochs3-lr001", epochs=3, lr0=0.01)
    submit(run_name="epochs5-lr001", epochs=5, lr0=0.01)

    print("\n✅ 2つのジョブを投入しました (epochs=3, epochs=5)")
    print("GCPコンソールで確認: https://console.cloud.google.com/vertex-ai/training/custom-jobs")
    print("実験結果の比較:      https://console.cloud.google.com/vertex-ai/experiments")
