#!/usr/bin/env python3
"""
Supabaseのテーブル存在確認スクリプト
DATABASE_DESIGN.mdで定義されているテーブルが実際に存在するか確認します。
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Tuple
from datetime import datetime

# プロジェクトルートをPythonパスに追加
sys.path.append(str(Path(__file__).parent.parent))

from src.utils.supabase_client import get_supabase_client
from supabase import Client

# DATABASE_DESIGN.mdで定義されているテーブル
REQUIRED_TABLES = [
    'profiles',
    'clients',
    'client_settings',
    'job_requirements',
    'search_jobs',
    'job_status_history',
    'candidates',
    'candidate_submissions',
    'search_results',
    'notification_settings',
    'retry_queue',
    'ai_evaluations',
    'searches',
    'scraping_sessions'  # コードで実際に使用されている
]

# コードで実際に使用されているテーブル（検索結果より）
USED_IN_CODE = [
    'profiles',
    'clients',
    'jobs',
    'job_requirements',
    'candidates',
    'scraping_sessions'
]


def check_table_exists(supabase: Client, table_name: str) -> Tuple[bool, str]:
    """
    テーブルの存在を確認
    
    Args:
        supabase: Supabaseクライアント
        table_name: テーブル名
        
    Returns:
        (存在するか, エラーメッセージ)
    """
    try:
        # テーブルから1件だけ取得を試みる
        result = supabase.table(table_name).select('*').limit(1).execute()
        return True, ""
    except Exception as e:
        error_msg = str(e)
        # テーブルが存在しない場合のエラーメッセージを確認
        if "relation" in error_msg and "does not exist" in error_msg:
            return False, "テーブルが存在しません"
        else:
            return False, f"エラー: {error_msg}"


def main():
    """メイン処理"""
    print("=" * 60)
    print("Supabaseテーブル存在確認")
    print(f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    try:
        # Supabaseクライアントを取得
        supabase = get_supabase_client()
        print("✅ Supabase接続成功\n")
    except Exception as e:
        print(f"❌ Supabase接続エラー: {e}")
        return
    
    # 結果を格納
    results = {
        "exists": [],
        "missing": [],
        "error": []
    }
    
    # 1. DATABASE_DESIGN.mdで定義されているテーブルの確認
    print("【DATABASE_DESIGN.mdで定義されているテーブル】")
    print("-" * 60)
    
    for table_name in REQUIRED_TABLES:
        exists, error_msg = check_table_exists(supabase, table_name)
        
        if exists:
            print(f"✅ {table_name:<25} - 存在します")
            results["exists"].append(table_name)
        else:
            if "存在しません" in error_msg:
                print(f"❌ {table_name:<25} - {error_msg}")
                results["missing"].append(table_name)
            else:
                print(f"⚠️  {table_name:<25} - {error_msg}")
                results["error"].append((table_name, error_msg))
    
    # 2. コードで使用されているが定義にないテーブルの確認
    print("\n【コードで使用されているテーブル】")
    print("-" * 60)
    
    additional_tables = set(USED_IN_CODE) - set(REQUIRED_TABLES)
    if additional_tables:
        for table_name in additional_tables:
            exists, error_msg = check_table_exists(supabase, table_name)
            
            if exists:
                print(f"⚠️  {table_name:<25} - 存在します（DATABASE_DESIGN.mdに定義なし）")
                results["exists"].append(table_name)
            else:
                print(f"❌ {table_name:<25} - {error_msg}（DATABASE_DESIGN.mdに定義なし）")
                results["missing"].append(table_name)
    
    # 3. サマリー
    print("\n【サマリー】")
    print("=" * 60)
    print(f"✅ 存在するテーブル: {len(results['exists'])}個")
    if results['exists']:
        for table in sorted(results['exists']):
            print(f"   - {table}")
    
    print(f"\n❌ 存在しないテーブル: {len(results['missing'])}個")
    if results['missing']:
        for table in sorted(results['missing']):
            print(f"   - {table}")
    
    print(f"\n⚠️  エラーが発生したテーブル: {len(results['error'])}個")
    if results['error']:
        for table, error in results['error']:
            print(f"   - {table}: {error}")
    
    # 4. 推奨事項
    if results['missing']:
        print("\n【推奨事項】")
        print("=" * 60)
        print("以下のテーブルを作成する必要があります：")
        for table in sorted(results['missing']):
            print(f"- {table}")
        print("\nSupabaseのダッシュボードまたはマイグレーションスクリプトを使用して")
        print("これらのテーブルを作成してください。")
    
    # 5. 注意事項
    if 'jobs' in results['exists'] and 'search_jobs' in results['missing']:
        print("\n【注意】")
        print("'jobs'テーブルが存在し、'search_jobs'が存在しません。")
        print("コード内で'jobs'を使用している箇所は'search_jobs'の可能性があります。")


if __name__ == "__main__":
    main()