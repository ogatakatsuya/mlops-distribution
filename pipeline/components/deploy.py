from kfp import dsl


@dsl.component(
    base_image="python:3.11-slim",
    packages_to_install=["google-cloud-aiplatform>=1.60.0"],
)
def deploy_model(
    project_id: str,
    region: str,
    model_resource_name: str,
    endpoint_id: str,
) -> str:
    """
    登録済みモデルを Vertex AI Endpoint へデプロイする。
    既存のデプロイ済みモデルを解除してから新モデルをトラフィック 100% でデプロイする。
    Endpoint ID は Terraform で固定されているため、アプリ側のコード変更は不要。
    """
    from google.cloud import aiplatform

    aiplatform.init(project=project_id, location=region)

    endpoint = aiplatform.Endpoint(endpoint_name=endpoint_id)
    model = aiplatform.Model(model_name=model_resource_name)

    # 既存のデプロイ済みモデルをすべて解除
    for deployed in endpoint.list_models():
        endpoint.undeploy(deployed_model_id=deployed.id)
        print(f"Undeployed: {deployed.id}")

    # 新モデルをデプロイ
    endpoint.deploy(
        model=model,
        machine_type="n1-standard-4",
        accelerator_type="NVIDIA_TESLA_T4",
        accelerator_count=1,
        traffic_percentage=100,
    )

    print(f"Model deployed to endpoint: {endpoint_id}")
    return endpoint_id
