#!/usr/bin/env python3
"""
WebApp起動スクリプト
"""
import os
import sys

# webappディレクトリをPythonパスに追加
webapp_dir = os.path.join(os.path.dirname(__file__), 'webapp')
sys.path.insert(0, webapp_dir)

# プロジェクトルートもパスに追加（coreモジュール用）
project_root = os.path.dirname(__file__)
sys.path.insert(0, project_root)

# 環境変数の読み込み（dotenvが利用可能な場合のみ）
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Warning: python-dotenv not installed. Using system environment variables.")
    print("To install: pip install python-dotenv")

# uvicornでアプリケーションを起動
try:
    import uvicorn
except ImportError:
    print("Error: uvicorn not installed.")
    print("Please install requirements: pip install -r requirements.txt")
    sys.exit(1)

if __name__ == "__main__":
    print(f"Starting WebApp from {webapp_dir}")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        app_dir=webapp_dir
    )