#!/bin/bash
# WebApp起動スクリプト（仮想環境対応）

echo "RPO Automation WebApp Starter"
echo "=============================="

# プロジェクトルートに移動
cd "$(dirname "$0")"

# 仮想環境の確認と有効化
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
else
    echo "Warning: No virtual environment found."
    echo "Create one with: python3 -m venv venv"
fi

# 必要なパッケージの確認
echo "Checking dependencies..."
python3 -c "import uvicorn" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Installing requirements..."
    pip install -r requirements.txt
fi

# 環境変数の読み込み
if [ -f .env ]; then
    echo "Loading environment variables..."
    # コメント行と空行を除外して環境変数を読み込む
    set -a
    source <(grep -v '^#' .env | grep -v '^$')
    set +a
fi

# PYTHONPATHの設定
export PYTHONPATH="$(pwd):$PYTHONPATH"

# WebAppの起動
echo "Starting WebApp on http://localhost:8000"
cd webapp
python3 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000