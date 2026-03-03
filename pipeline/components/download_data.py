from kfp import dsl


@dsl.component(
    base_image="python:3.11-slim",
    packages_to_install=["google-cloud-storage>=2.16.0"],
)
def validate_data(
    project_id: str,
    data_bucket: str,
    data_version: str,
) -> str:
    """GCS 上のデータセットの存在を確認し、データパス（GCS URI）を返す"""
    from google.cloud import storage

    client = storage.Client(project=project_id)
    bucket = client.bucket(data_bucket)
    prefix = f"datasets/{data_version}/"
    blobs = list(bucket.list_blobs(prefix=prefix))

    if not blobs:
        raise ValueError(f"Dataset not found: gs://{data_bucket}/{prefix}")

    data_path = f"gs://{data_bucket}/{prefix}"
    print(f"Dataset validated: {len(blobs)} files at {data_path}")
    return data_path
