FROM python:3.11-slim

WORKDIR /app

# uv をインストール
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# OpenCV (ultralytics の依存) がサーバー環境で必要とする X11 ライブラリ
RUN apt-get update && apt-get install -y --no-install-recommends \
    libxcb1 \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# PyTorch CPU ビルド (GPU を使わないためサイズを削減)
RUN uv pip install --system --no-cache \
    torch torchvision \
    --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt

COPY train.py .

ENTRYPOINT ["python", "train.py"]
