#!/usr/bin/env python3
"""
Supabaseの現在のテーブル構造を確認するスクリプト
"""
from dotenv import load_dotenv
import os
from supabase import create_client

# .envファイルを読み込む
load_dotenv()

# 環境変数を取得
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

if not supabase_url or not supabase_key:
    print("Error: SUPABASE_URL or SUPABASE_SERVICE_KEY not set")
    exit(1)

print("=== Supabaseテーブル構造確認 ===\n")

try:
    # Supabaseクライアントを作成
    supabase = create_client(supabase_url, supabase_key)
    
    # 既知のテーブルをチェック
    tables_to_check = ['profiles', 'clients', 'requirements', 'candidates', 'search_jobs', 'search_results']
    
    for table_name in tables_to_check:
        try:
            # テーブルから1件だけ取得してカラムを確認
            result = supabase.table(table_name).select("*").limit(1).execute()
            print(f"✅ {table_name} テーブル: 存在します")
            
            if result.data:
                print(f"   カラム: {list(result.data[0].keys())}")
            else:
                # データがない場合は、エラーを発生させて構造を確認
                try:
                    # 存在しないIDで検索することで、エラーメッセージからカラムを推測
                    supabase.table(table_name).select("*").eq('id', '00000000-0000-0000-0000-000000000000').execute()
                except Exception as e:
                    print(f"   (データなし)")
            print()
            
        except Exception as e:
            error_msg = str(e)
            if "relation" in error_msg and "does not exist" in error_msg:
                print(f"❌ {table_name} テーブル: 存在しません")
            else:
                print(f"⚠️  {table_name} テーブル: エラー - {error_msg}")
            print()
    
except Exception as e:
    print(f"エラーが発生しました: {type(e).__name__}")
    print(f"詳細: {str(e)}")