"""
Vertex AI Pipelines へパイプラインをコンパイルして投入し、即終了する。

Cloud Build から呼び出される。パイプライン完了は待たない。
Vertex AI が training → deploy を非同期に管理する。

環境変数:
  PROJECT_ID      : GCP プロジェクト ID (必須)
  REGION          : リージョン (デフォルト: asia-northeast1)
  DATA_BUCKET     : 学習データ・モデル用 GCS バケット名 (必須)
  PIPELINE_BUCKET : Vertex AI Pipelines のルート用 GCS バケット名 (必須)
  TRAINER_IMAGE   : 学習コンテナ URI
  SERVING_IMAGE   : 推論コンテナ URI
  ENDPOINT_ID     : Cloud Run サービス名 (例: vtuber-detector)
  BUILD_ID        : Cloud Build ビルド ID (パイプライン実行の識別子)
  VERTEX_SA       : パイプラインで使用するサービスアカウント (省略可)
  WANDB_API_KEY   : Weights & Biases API キー (省略可)
  WANDB_PROJECT   : W&B プロジェクト名 (デフォルト: vtuber-detector)
"""
import os
import yaml
from kfp import compiler
from google.cloud import aiplatform
from pipeline.definition import vtuber_pipeline

PROJECT_ID      = os.environ["PROJECT_ID"]
REGION          = os.environ.get("REGION", "asia-northeast1")
DATA_BUCKET     = os.environ["DATA_BUCKET"]
PIPELINE_BUCKET = os.environ["PIPELINE_BUCKET"]
TRAINER_IMAGE   = os.environ["TRAINER_IMAGE"]
SERVING_IMAGE   = os.environ["SERVING_IMAGE"]
SERVICE_NAME    = os.environ["ENDPOINT_ID"]   # Cloud Run サービス名として使用
BUILD_ID        = os.environ.get("BUILD_ID", "local")
VERTEX_SA       = os.environ.get("VERTEX_SA", "")
WANDB_API_KEY   = os.environ.get("WANDB_API_KEY", "")
WANDB_PROJECT   = os.environ.get("WANDB_PROJECT", "vtuber-detector")

with open("pipeline/config.yaml") as f:
    config = yaml.safe_load(f)

# ── パイプラインをコンパイル ──────────────────────────────────────────────
pipeline_json = "/tmp/pipeline.json"
compiler.Compiler().compile(vtuber_pipeline, pipeline_json)
print(f"Pipeline compiled: {pipeline_json}")

# ── Vertex AI Pipelines へ投入 (ノンブロッキング) ─────────────────────────
aiplatform.init(project=PROJECT_ID, location=REGION)

job = aiplatform.PipelineJob(
    display_name=f"vtuber-pipeline-{BUILD_ID}",
    template_path=pipeline_json,
    pipeline_root=f"gs://{PIPELINE_BUCKET}",
    parameter_values={
        "project":             PROJECT_ID,
        "region":              REGION,
        "data_bucket":         DATA_BUCKET,
        "dataset_version":     str(config["dataset"]["version"]),
        "trainer_image":       TRAINER_IMAGE,
        "serving_image":   SERVING_IMAGE,
        "service_name":    SERVICE_NAME,
        "build_id":        BUILD_ID,
        "epochs":          config["model"]["epochs"],
        "batch_size":      config["model"]["batch_size"],
        "image_size":      config["model"]["image_size"],
        "model_arch":      config["model"]["architecture"],
        "machine_type":    config.get("training", {}).get("machine_type", "n1-highmem-4"),
        "service_account": VERTEX_SA,
        "wandb_api_key":   WANDB_API_KEY,
        "wandb_project":   WANDB_PROJECT,
    },
)

job.submit(service_account=VERTEX_SA or None)

print(f"\nPipeline submitted!")
print(f"Resource : {job.resource_name}")
print(f"Console  : https://console.cloud.google.com/vertex-ai/locations/{REGION}/pipelines/runs?project={PROJECT_ID}")
