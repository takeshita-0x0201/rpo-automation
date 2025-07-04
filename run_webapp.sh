#!/bin/bash
# WebApp起動スクリプト

echo "RPO Automation WebApp を起動します..."

# 仮想環境をアクティベート
source venv/bin/activate

# WebAppを起動
echo "FastAPIサーバーを起動中..."
echo "ブラウザで http://localhost:8000 にアクセスしてください"
echo "APIドキュメント: http://localhost:8000/docs"
echo "終了するには Ctrl+C を押してください"
echo ""

python -m uvicorn src.web.main:app --reload --host 0.0.0.0 --port 8000