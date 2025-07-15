#!/bin/bash
# WebApp起動スクリプト

# スクリプトのディレクトリを取得
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
WEBAPP_DIR="$SCRIPT_DIR"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# プロジェクトルートに移動
cd "$PROJECT_ROOT"

# 環境変数の読み込み
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Pythonパスの設定
export PYTHONPATH="${PROJECT_ROOT}:${WEBAPP_DIR}"

# アプリケーション起動
echo "Starting WebApp on http://localhost:8000"
cd "$WEBAPP_DIR"
uvicorn main:app --reload --host 0.0.0.0 --port 8000