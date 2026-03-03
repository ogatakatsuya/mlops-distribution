from kfp import dsl


@dsl.component(
    base_image="python:3.11-slim",
    packages_to_install=["google-cloud-aiplatform>=1.60.0"],
)
def register_model(
    project_id: str,
    region: str,
    data_bucket: str,
    run_name: str,
) -> str:
    """
    学習済みモデルを Vertex AI Model Registry に登録する。
    登録後のモデルリソース名（フルパス）を返す。

    serving_container_image_uri には serve/ で構築した YOLO 推論コンテナを指定する。
    Phase 0 で手動ビルド済みの前提:
      docker build -t {region}-docker.pkg.dev/{project}/mlops/vtuber-predictor:latest serve/
      docker push {region}-docker.pkg.dev/{project}/mlops/vtuber-predictor:latest
    """
    from google.cloud import aiplatform

    aiplatform.init(project=project_id, location=region)

    serving_image = (
        f"asia-northeast1-docker.pkg.dev/{project_id}/mlops/vtuber-predictor:latest"
    )

    model = aiplatform.Model.upload(
        display_name=f"vtuber-detector-{run_name}",
        artifact_uri=f"gs://{data_bucket}/models/{run_name}",
        serving_container_image_uri=serving_image,
        serving_container_predict_route="/predict",
        serving_container_health_route="/health",
        serving_container_ports=[8080],
        labels={"pipeline_run": run_name},
    )

    print(f"Model registered: {model.resource_name}")
    return model.resource_name
