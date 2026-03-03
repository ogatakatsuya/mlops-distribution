"""
Vertex AI Endpoint 用 YOLO 推論サーバー。

起動時に AIP_STORAGE_URI（モデルアーティファクトの GCS パス）から
best.pt をダウンロードして YOLO モデルをロードする。

リクエスト形式:
  POST /predict
  {"instances": [{"image": "<base64エンコード画像>"}]}

レスポンス形式:
  {"predictions": [{"boxes": [{"x1":..,"y1":..,"x2":..,"y2":..,"confidence":..,"class_name":..}]}]}
"""
import base64
import io
import os

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from google.cloud import storage
from PIL import Image
from ultralytics import YOLO

app = FastAPI()
_model: YOLO | None = None


def _load_model() -> YOLO:
    """AIP_STORAGE_URI から best.pt をダウンロードして YOLO をロードする"""
    artifact_uri = os.environ.get("AIP_STORAGE_URI", "").rstrip("/")
    if not artifact_uri.startswith("gs://"):
        raise RuntimeError(f"AIP_STORAGE_URI が未設定または無効: {artifact_uri!r}")

    model_path = "/tmp/best.pt"
    gcs_path = artifact_uri[5:]  # "gs://" を除去
    bucket_name, prefix = gcs_path.split("/", 1)
    blob_path = f"{prefix}/best.pt"

    client = storage.Client()
    client.bucket(bucket_name).blob(blob_path).download_to_filename(model_path)
    print(f"Model downloaded: {artifact_uri}/best.pt → {model_path}")

    return YOLO(model_path)


@app.on_event("startup")
async def startup() -> None:
    global _model
    _model = _load_model()
    print("YOLO model ready.")


@app.get(os.environ.get("AIP_HEALTH_ROUTE", "/health"))
def health() -> dict:
    return {"status": "healthy"}


@app.post(os.environ.get("AIP_PREDICT_ROUTE", "/predict"))
async def predict(request: Request) -> JSONResponse:
    body = await request.json()
    predictions = []

    for instance in body.get("instances", []):
        image_bytes = base64.b64decode(instance["image"])
        image = Image.open(io.BytesIO(image_bytes))
        results = _model(image)[0]

        boxes = [
            {
                "x1":         float(b.xyxy[0][0]),
                "y1":         float(b.xyxy[0][1]),
                "x2":         float(b.xyxy[0][2]),
                "y2":         float(b.xyxy[0][3]),
                "confidence": float(b.conf[0]),
                "class_id":   int(b.cls[0]),
                "class_name": results.names[int(b.cls[0])],
            }
            for b in results.boxes
        ]
        predictions.append({"boxes": boxes})

    return JSONResponse({"predictions": predictions})
