"""
MLOps 勉強会デモ: YOLO Bounding Box Visualizer

2つのモードに対応:
  - Local モード : ultralytics YOLO をその場で実行
  - API モード   : serve/ の /predict エンドポイントを呼び出し
"""

import base64
import io

import cv2
import numpy as np
import requests
import streamlit as st
from PIL import Image
from ultralytics import YOLO

# ------------------------------------------------------------------ #
# ページ設定
# ------------------------------------------------------------------ #
st.set_page_config(
    page_title="YOLO Bounding Box Demo",
    page_icon="🎯",
    layout="wide",
)

# ------------------------------------------------------------------ #
# サイドバー
# ------------------------------------------------------------------ #
st.sidebar.title("設定")

mode = st.sidebar.radio(
    "推論モード",
    ["Local (ultralytics)", "API (serve endpoint)"],
    help="Local: ローカルで YOLO を直接実行\nAPI: デプロイ済みエンドポイントを呼び出し",
)

if mode == "Local (ultralytics)":
    model_name = st.sidebar.selectbox(
        "モデル",
        ["yolo26n.pt", "yolov8n.pt", "yolov8s.pt", "yolov8m.pt"],
        help="yolo26n: 学習に使用したモデル（推奨）",
    )
    conf_threshold = st.sidebar.slider(
        "Confidence しきい値", 0.0, 1.0, 0.25, 0.05
    )
else:
    api_url = st.sidebar.text_input(
        "API エンドポイント URL",
        value="http://localhost:8080/predict",
        help="serve/ の FastAPI サーバーの /predict URL",
    )
    conf_threshold = st.sidebar.slider(
        "Confidence しきい値 (表示フィルタ)", 0.0, 1.0, 0.25, 0.05
    )

box_thickness = st.sidebar.slider("Bounding Box の太さ", 1, 6, 2)
font_scale = st.sidebar.slider("ラベルのフォントサイズ", 0.3, 1.5, 0.6, 0.1)

# ------------------------------------------------------------------ #
# カラーパレット (クラス ID ごとに固定色)
# ------------------------------------------------------------------ #
_PALETTE = [
    (255, 56, 56), (255, 157, 151), (255, 112, 31), (255, 178, 29),
    (207, 210, 49), (72, 249, 10), (146, 204, 23), (61, 219, 134),
    (26, 147, 52), (0, 212, 187), (44, 153, 168), (0, 194, 255),
    (52, 69, 147), (100, 115, 255), (0, 24, 236), (132, 56, 255),
    (82, 0, 133), (203, 56, 255), (255, 149, 200), (255, 55, 198),
]


def get_color(class_id: int) -> tuple:
    return _PALETTE[class_id % len(_PALETTE)]


# ------------------------------------------------------------------ #
# 描画ユーティリティ
# ------------------------------------------------------------------ #
def draw_boxes(image: np.ndarray, boxes: list[dict]) -> np.ndarray:
    """boxes リストから bounding box を画像に描画して返す。"""
    img = image.copy()
    for box in boxes:
        x1, y1, x2, y2 = int(box["x1"]), int(box["y1"]), int(box["x2"]), int(box["y2"])
        conf = box["confidence"]
        class_id = box.get("class_id", 0)
        class_name = box.get("class_name", str(class_id))
        color = get_color(class_id)

        cv2.rectangle(img, (x1, y1), (x2, y2), color, box_thickness)

        label = f"{class_name} {conf:.2f}"
        (tw, th), baseline = cv2.getTextSize(
            label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 1
        )
        label_y = max(y1, th + 4)
        cv2.rectangle(img, (x1, label_y - th - 4), (x1 + tw, label_y + baseline), color, -1)
        cv2.putText(
            img, label,
            (x1, label_y - 2),
            cv2.FONT_HERSHEY_SIMPLEX, font_scale,
            (255, 255, 255), 1, cv2.LINE_AA,
        )
    return img


# ------------------------------------------------------------------ #
# 推論ヘルパー
# ------------------------------------------------------------------ #
@st.cache_resource
def load_yolo(model_name: str) -> YOLO:
    return YOLO(model_name)


def infer_local(pil_image: Image.Image, model_name: str, conf: float) -> list[dict]:
    model = load_yolo(model_name)
    results = model(pil_image, conf=conf)[0]
    boxes = []
    for b in results.boxes:
        boxes.append({
            "x1":         float(b.xyxy[0][0]),
            "y1":         float(b.xyxy[0][1]),
            "x2":         float(b.xyxy[0][2]),
            "y2":         float(b.xyxy[0][3]),
            "confidence": float(b.conf[0]),
            "class_id":   int(b.cls[0]),
            "class_name": results.names[int(b.cls[0])],
        })
    return boxes


def infer_api(pil_image: Image.Image, url: str, conf: float) -> list[dict]:
    buf = io.BytesIO()
    pil_image.save(buf, format="JPEG")
    encoded = base64.b64encode(buf.getvalue()).decode()

    resp = requests.post(url, json={"instances": [{"image": encoded}]}, timeout=30)
    resp.raise_for_status()
    raw_boxes = resp.json()["predictions"][0]["boxes"]
    # confidence しきい値でフィルタ
    return [b for b in raw_boxes if b["confidence"] >= conf]


# ------------------------------------------------------------------ #
# メイン UI
# ------------------------------------------------------------------ #
st.title("🎯 YOLO Bounding Box Visualizer")
st.caption("MLOps 勉強会デモ — 画像をアップロードすると YOLO が物体を検出します")

uploaded = st.file_uploader(
    "画像をアップロード", type=["jpg", "jpeg", "png", "bmp", "webp"]
)

if uploaded is not None:
    pil_image = Image.open(uploaded).convert("RGB")
    img_np = np.array(pil_image)

    col_orig, col_result = st.columns(2)

    with col_orig:
        st.subheader("入力画像")
        st.image(pil_image, width="stretch")

    with st.spinner("推論中..."):
        try:
            if mode == "Local (ultralytics)":
                boxes = infer_local(pil_image, model_name, conf_threshold)
            else:
                boxes = infer_api(pil_image, api_url, conf_threshold)
            error_msg = None
        except Exception as e:
            boxes = []
            error_msg = str(e)

    if error_msg:
        st.error(f"推論エラー: {error_msg}")
    else:
        result_img = draw_boxes(img_np, boxes)

        with col_result:
            st.subheader(f"検出結果 ({len(boxes)} 件)")
            st.image(result_img, channels="RGB", width="stretch")

        # 検出結果テーブル
        if boxes:
            st.subheader("検出ボックス詳細")
            table_data = [
                {
                    "クラス": b["class_name"],
                    "Confidence": f"{b['confidence']:.3f}",
                    "x1": int(b["x1"]),
                    "y1": int(b["y1"]),
                    "x2": int(b["x2"]),
                    "y2": int(b["y2"]),
                    "幅": int(b["x2"] - b["x1"]),
                    "高さ": int(b["y2"] - b["y1"]),
                }
                for b in sorted(boxes, key=lambda x: -x["confidence"])
            ]
            st.dataframe(table_data, width="stretch")

        else:
            st.info("検出なし（confidence しきい値を下げてみてください）")
else:
    st.info("サイドバーで設定を選択し、上の枠に画像をドラッグ＆ドロップしてください。")

    with st.expander("アーキテクチャ説明（MLOps 勉強会用）"):
        st.markdown("""
        ### このデモの構成

        ```
        ┌─────────────┐       Local モード        ┌──────────────────┐
        │  Streamlit  │ ─────────────────────────▶ │  ultralytics     │
        │  (demo/)    │                            │  YOLO (ローカル)  │
        └─────────────┘                            └──────────────────┘

        ┌─────────────┐        API モード          ┌──────────────────┐
        │  Streamlit  │ ─── POST /predict ────────▶ │  FastAPI         │
        │  (demo/)    │     (base64 image)          │  (serve/)        │
        └─────────────┘                            └──────────────────┘
                                                          │
                                                          ▼
                                                   ┌──────────────────┐
                                                   │  YOLO model      │
                                                   │  (GCS / Vertex)  │
                                                   └──────────────────┘
        ```

        **Local モード**: `ultralytics` を直接呼び出し、モデルを自動ダウンロード。
        素早くプロトタイプしたい場合やオフライン環境向け。

        **API モード**: `serve/` の FastAPI コンテナを呼び出す。
        Vertex AI Endpoint にデプロイした本番環境や、Docker で起動したローカルサーバーに対応。
        """)
