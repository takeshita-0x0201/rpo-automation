# WebApp用のDockerfile
FROM python:3.9-slim

WORKDIR /app

# システムの依存関係をインストール
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Pythonの依存関係をインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー
COPY src/ ./src/
COPY config/ ./config/

# FastAPIアプリケーションを起動
CMD ["uvicorn", "src.web.main:app", "--host", "0.0.0.0", "--port", "8080"]