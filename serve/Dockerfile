FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

# Vertex AI は AIP_HTTP_PORT で起動ポートを指示する（デフォルト 8080）
EXPOSE 8080
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${AIP_HTTP_PORT:-8080}"]
