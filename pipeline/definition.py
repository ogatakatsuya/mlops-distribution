#!/usr/bin/env python3
"""
Vertex AI Pipelines パイプライン定義。
Cloud Build から自動実行、またはローカルから手動実行も可能。

使い方:
  export PROJECT_ID=<your-project>
  export ENDPOINT_ID=$(cd terraform && terraform output -raw endpoint_id)
  python pipeline/definition.py --project_id=$PROJECT_ID --endpoint_id=$ENDPOINT_ID
"""
import argparse
import datetime
import sys
from pathlib import Path

import yaml
from google.cloud import aiplatform
from kfp import compiler, dsl

# Cloud Build・ローカル問わず import が通るようプロジェクトルートを追加
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.components.download_data import validate_data
from pipeline.components.train import train_model
from pipeline.components.evaluate import check_accuracy
from pipeline.components.register import register_model
from pipeline.components.deploy import deploy_model


@dsl.pipeline(
    name="vtuber-detection-pipeline",
    description="VTuberキャラクター検出モデルの学習・評価・デプロイ自動化パイプライン",
)
def vtuber_pipeline(
    project_id: str,
    region: str,
    data_bucket: str,
    data_version: str,
    experiment: str,
    run_name: str,
    epochs: int,
    lr0: float,
    freeze: int,
    imgsz: int,
    patience: int,
    map_threshold: float,
    machine_type: str,
    accelerator_type: str,
    endpoint_id: str,
    vertex_ai_sa: str,
) -> None:
    # Step 1: データセット確認
    validate_op = validate_data(
        project_id=project_id,
        data_bucket=data_bucket,
        data_version=data_version,
    )

    # Step 2: YOLO26n 転移学習（GPU Custom Training Job として実行）
    train_op = train_model(
        project_id=project_id,
        region=region,
        data_bucket=data_bucket,
        data_version=data_version,
        run_name=run_name,
        epochs=epochs,
        lr0=lr0,
        freeze=freeze,
        imgsz=imgsz,
        patience=patience,
        experiment=experiment,
        vertex_ai_sa=vertex_ai_sa,
    ).after(validate_op)

    # Step 3: mAP50 が閾値を超えているか評価
    eval_op = check_accuracy(
        mAP50=train_op.output,
        threshold=map_threshold,
    )

    # Step 4 & 5: 閾値通過時のみ Model Registry 登録 → Endpoint デプロイ
    with dsl.Condition(eval_op.output == "deploy", name="accuracy-gate"):
        register_op = register_model(
            project_id=project_id,
            region=region,
            data_bucket=data_bucket,
            run_name=run_name,
        )
        deploy_model(
            project_id=project_id,
            region=region,
            model_resource_name=register_op.output,
            endpoint_id=endpoint_id,
        ).after(register_op)


def main() -> None:
    parser = argparse.ArgumentParser(description="パイプラインをコンパイルして Vertex AI へ投入")
    parser.add_argument("--project_id", required=True)
    parser.add_argument("--region", default="asia-northeast1")
    parser.add_argument("--endpoint_id", required=True)
    args = parser.parse_args()

    cfg = yaml.safe_load((ROOT / "pipeline" / "config.yaml").read_text())

    data_bucket   = f"{args.project_id}-mlops-data"
    pipeline_root = f"gs://{args.project_id}-mlops-pipeline/runs"
    vertex_ai_sa  = f"mlops-vertex-ai@{args.project_id}.iam.gserviceaccount.com"
    run_name      = datetime.datetime.utcnow().strftime("run-%Y%m%d-%H%M%S")

    # コンパイル
    pipeline_path = "/tmp/vtuber_pipeline.json"
    compiler.Compiler().compile(vtuber_pipeline, pipeline_path)
    print(f"Pipeline compiled → {pipeline_path}")

    # Vertex AI Pipelines へ投入
    aiplatform.init(project=args.project_id, location=args.region)
    job = aiplatform.PipelineJob(
        display_name=f"vtuber-pipeline-{run_name}",
        template_path=pipeline_path,
        pipeline_root=pipeline_root,
        parameter_values={
            "project_id":      args.project_id,
            "region":          args.region,
            "data_bucket":     data_bucket,
            "data_version":    cfg["data_version"],
            "experiment":      "yolo26-vtuber",
            "run_name":        run_name,
            "epochs":          cfg["epochs"],
            "lr0":             cfg["lr0"],
            "freeze":          cfg["freeze"],
            "imgsz":           cfg.get("imgsz", 640),
            "patience":        cfg.get("patience", 10),
            "map_threshold":   cfg["map_threshold"],
            "machine_type":    cfg["machine_type"],
            "accelerator_type": cfg["accelerator_type"],
            "endpoint_id":     args.endpoint_id,
            "vertex_ai_sa":    vertex_ai_sa,
        },
    )
    job.submit()
    print(f"Pipeline submitted: {job.resource_name}")
    print("Monitor: https://console.cloud.google.com/vertex-ai/pipelines")


if __name__ == "__main__":
    main()
