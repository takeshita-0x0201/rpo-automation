# WebApp用のDockerfile
FROM python:3.11-slim

WORKDIR /app

# システムの依存関係をインストール
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Pythonの依存関係をインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Playwrightのブラウザをインストール（スクレイピング用）
RUN playwright install chromium
RUN playwright install-deps

# アプリケーションコードをコピー
COPY src/ ./src/
COPY migrations/ ./migrations/
COPY config/ ./config/
COPY .env.example .env

# 非rootユーザーの作成
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# 環境変数
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# FastAPIアプリケーションを起動
CMD ["uvicorn", "src.web.main:app", "--host", "0.0.0.0", "--port", "8080"]