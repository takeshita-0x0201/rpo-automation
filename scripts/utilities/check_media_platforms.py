#!/usr/bin/env python3
"""
media_platformsテーブルの状態を確認するスクリプト
"""
import os
import sys
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.utils.supabase_client import get_supabase_client
import requests

def check_database():
    """データベースの状態を確認"""
    print("=== データベース確認 ===")
    try:
        supabase = get_supabase_client()
        
        # テーブルの存在確認
        print("\n1. media_platformsテーブルの確認...")
        try:
            response = supabase.table("media_platforms").select("*").execute()
            print(f"✅ テーブルが存在します。レコード数: {len(response.data)}")
            
            if response.data:
                print("\n登録されているプラットフォーム:")
                for platform in response.data:
                    status = "🟢 アクティブ" if platform.get('is_active') else "🔴 非アクティブ"
                    print(f"  - {platform.get('display_name')} ({platform.get('name')}) {status}")
                    if platform.get('url_patterns'):
                        print(f"    URLパターン: {platform.get('url_patterns')}")
            else:
                print("⚠️  テーブルは存在しますが、データがありません")
                
        except Exception as e:
            print(f"❌ テーブルアクセスエラー: {str(e)}")
            
    except Exception as e:
        print(f"❌ データベース接続エラー: {str(e)}")

def check_api():
    """APIエンドポイントの確認"""
    print("\n\n=== APIエンドポイント確認 ===")
    try:
        response = requests.get("http://localhost:8000/api/media_platforms")
        print(f"ステータスコード: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ APIは正常に動作しています")
            print(f"レスポンス: {data}")
        else:
            print(f"❌ APIエラー: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ APIサーバーに接続できません。サーバーが起動していることを確認してください。")
    except Exception as e:
        print(f"❌ エラー: {str(e)}")

def check_table_structure():
    """テーブル構造の確認"""
    print("\n\n=== テーブル構造確認 ===")
    try:
        supabase = get_supabase_client()
        
        # 1レコード取得してカラムを確認
        response = supabase.table("media_platforms").select("*").limit(1).execute()
        
        if response.data:
            columns = list(response.data[0].keys())
            print("カラム一覧:")
            for col in columns:
                print(f"  - {col}")
            
            # url_patternsカラムの確認
            if 'url_patterns' in columns:
                print("✅ url_patternsカラムが存在します")
            else:
                print("⚠️  url_patternsカラムが存在しません")
                
    except Exception as e:
        print(f"❌ エラー: {str(e)}")

if __name__ == "__main__":
    print("media_platformsテーブルの診断を開始します...\n")
    
    check_database()
    check_api()
    check_table_structure()
    
    print("\n\n診断完了！")
    print("\nもしデータが存在しない場合は、以下のコマンドでデータを投入してください:")
    print("  python scripts/setup/setup_media_platforms.py")