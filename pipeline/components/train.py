from kfp import dsl


@dsl.component(
    base_image="python:3.11-slim",
    packages_to_install=[
        "google-cloud-aiplatform>=1.60.0",
        "google-cloud-storage>=2.16.0",
    ],
)
def train_model(
    project_id: str,
    region: str,
    data_bucket: str,
    data_version: str,
    run_name: str,
    epochs: int,
    lr0: float,
    freeze: int,
    imgsz: int,
    patience: int,
    experiment: str,
    vertex_ai_sa: str,
) -> float:
    """
    src/train.py を Vertex AI Custom Training Job として GPU 上で実行する。
    完了後、train.py が GCS に保存した metrics.json から mAP50 を取得して返す。

    パイプラインコンテナ内には train.py が存在しないため、
    cloudbuild.yaml が事前に GCS へアップロードしたものを参照する。
    """
    import json
    import tempfile

    from google.cloud import aiplatform, storage

    aiplatform.init(project=project_id, location=region)
    gcs = storage.Client(project=project_id)
    bucket = gcs.bucket(data_bucket)

    # GCS から学習スクリプトをダウンロード
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="wb") as f:
        bucket.blob("scripts/train.py").download_to_filename(f.name)
        script_path = f.name

    job = aiplatform.CustomTrainingJob(
        display_name=f"pipeline-yolo26-{run_name}",
        script_path=script_path,
        container_uri="us-docker.pkg.dev/vertex-ai/training/pytorch-gpu.2-2:latest",
        requirements=[
            "ultralytics",
            "google-cloud-aiplatform>=1.60.0",
            "google-cloud-storage>=2.16.0",
            "pyyaml>=6.0",
        ],
        staging_bucket=f"gs://{data_bucket}",
    )

    job.run(
        args=[
            f"--project_id={project_id}",
            f"--region={region}",
            f"--data_bucket={data_bucket}",
            f"--data_version={data_version}",
            f"--experiment={experiment}",
            f"--run_name={run_name}",
            f"--epochs={epochs}",
            f"--lr0={lr0}",
            f"--freeze={freeze}",
            f"--imgsz={imgsz}",
            f"--patience={patience}",
        ],
        machine_type="n1-standard-4",
        accelerator_type="NVIDIA_TESLA_T4",
        accelerator_count=1,
        service_account=vertex_ai_sa,
        sync=True,  # パイプラインステップはジョブ完了まで待機
    )

    # train.py が GCS に保存した metrics.json を読み取る
    metrics = json.loads(bucket.blob(f"models/{run_name}/metrics.json").download_as_text())
    mAP50 = float(metrics.get("mAP50", 0.0))
    print(f"mAP50 = {mAP50:.4f}")
    return mAP50
