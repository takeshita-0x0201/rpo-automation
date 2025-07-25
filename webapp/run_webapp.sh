#!/bin/bash
# WebApp起動スクリプト

# スクリプトのディレクトリを取得
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
WEBAPP_DIR="$SCRIPT_DIR"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# ポート番号
PORT=8000

# 既存のプロセスをチェックして終了
echo "Checking for existing processes on port $PORT..."
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null ; then
    echo "Port $PORT is already in use. Killing existing process..."
    lsof -Pi :$PORT -sTCP:LISTEN -t | xargs kill -9
    sleep 2
fi

# プロジェクトルートに移動
cd "$PROJECT_ROOT"

# 環境変数の読み込み
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Pythonパスの設定
export PYTHONPATH="${PROJECT_ROOT}:${WEBAPP_DIR}"

# アプリケーション起動
echo "Starting WebApp on http://localhost:$PORT"
cd "$WEBAPP_DIR"

# エラー時の自動再起動とより詳細なログ
while true; do
    uvicorn main:app --reload --host 0.0.0.0 --port $PORT --log-level info
    echo "Server stopped. Restarting in 5 seconds..."
    sleep 5
done