"""
Vertex AI Pipelines パイプライン定義。

コンポーネント:
  train_component  : Custom Training Job を投入して完了を待つ (Vertex AI が管理)
  deploy_component : Cloud Run サービスのイメージと AIP_STORAGE_URI を更新する
"""
from kfp import dsl


@dsl.component(
    base_image="python:3.11-slim",
    packages_to_install=["google-cloud-aiplatform"],
)
def train_component(
    project: str,
    region: str,
    data_bucket: str,
    dataset_version: str,
    trainer_image: str,
    epochs: int,
    batch_size: int,
    image_size: int,
    model_arch: str,
    machine_type: str,
    service_account: str,
    build_id: str,
    wandb_api_key: str = "",
    wandb_project: str = "vtuber-detector",
) -> str:
    """Custom Training Job を投入して完了を待ち、モデル出力先 GCS URI を返す。"""
    from google.cloud import aiplatform

    model_gcs_dir = f"gs://{data_bucket}/models/{build_id}"

    aiplatform.init(
        project=project,
        location=region,
        staging_bucket=f"gs://{data_bucket}",
    )

    job = aiplatform.CustomContainerTrainingJob(
        display_name=f"yolo-train-{build_id}",
        container_uri=trainer_image,
    )

    env_vars = {
        "DATA_BUCKET":     data_bucket,
        "DATASET_VERSION": dataset_version,
        "EPOCHS":          str(epochs),
        "BATCH":           str(batch_size),
        "IMGSZ":           str(image_size),
        "MODEL":           model_arch + ".pt",
        "BUILD_ID":        build_id,
        "WANDB_PROJECT":   wandb_project,
    }
    if wandb_api_key:
        env_vars["WANDB_API_KEY"] = wandb_api_key

    job.run(
        base_output_dir=model_gcs_dir,
        machine_type=machine_type,
        replica_count=1,
        environment_variables=env_vars,
        service_account=service_account or None,
        sync=True,
    )

    return model_gcs_dir


@dsl.component(
    base_image="python:3.11-slim",
    packages_to_install=["google-cloud-run"],
)
def deploy_component(
    project: str,
    region: str,
    service_name: str,
    serving_image: str,
    model_gcs_dir: str,
):
    """Cloud Run サービスのコンテナイメージと AIP_STORAGE_URI を更新する。"""
    from google.cloud import run_v2

    artifact_uri = model_gcs_dir.rstrip("/") + "/model"

    client = run_v2.ServicesClient()
    service_resource = f"projects/{project}/locations/{region}/services/{service_name}"

    service = client.get_service(name=service_resource)

    container = service.template.containers[0]
    container.image = serving_image

    env_map = {e.name: e.value for e in container.env}
    env_map["AIP_STORAGE_URI"] = artifact_uri
    container.env = [run_v2.EnvVar(name=k, value=v) for k, v in env_map.items()]

    operation = client.update_service(service=service)
    updated = operation.result()

    print(f"Deployed: {updated.uri}")


@dsl.pipeline(name="vtuber-detector-pipeline")
def vtuber_pipeline(
    project: str,
    region: str,
    data_bucket: str,
    dataset_version: str,
    trainer_image: str,
    serving_image: str,
    service_name: str,
    build_id: str,
    epochs: int = 5,
    batch_size: int = 16,
    image_size: int = 640,
    model_arch: str = "yolov8n",
    machine_type: str = "n1-highmem-4",
    service_account: str = "",
    wandb_api_key: str = "",
    wandb_project: str = "vtuber-detector",
):
    train_task = train_component(
        project=project,
        region=region,
        data_bucket=data_bucket,
        dataset_version=dataset_version,
        trainer_image=trainer_image,
        epochs=epochs,
        batch_size=batch_size,
        image_size=image_size,
        model_arch=model_arch,
        machine_type=machine_type,
        service_account=service_account,
        build_id=build_id,
        wandb_api_key=wandb_api_key,
        wandb_project=wandb_project,
    )

    deploy_component(
        project=project,
        region=region,
        service_name=service_name,
        serving_image=serving_image,
        model_gcs_dir=train_task.output,
    ).after(train_task)
