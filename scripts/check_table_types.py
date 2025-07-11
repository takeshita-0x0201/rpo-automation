#!/usr/bin/env python3
"""
Supabaseのテーブルのカラム型を確認するスクリプト
外部キー制約のために必要な型情報を取得します
"""

import os
import sys
from pathlib import Path

# プロジェクトルートをPythonパスに追加
sys.path.append(str(Path(__file__).parent.parent))

from src.utils.supabase_client import get_supabase_client

def get_table_schema_info():
    """
    主要テーブルのスキーマ情報を取得
    """
    supabase = get_supabase_client()
    
    # 調査対象のテーブル
    tables_to_check = [
        'profiles',
        'clients', 
        'job_requirements',
        'candidates',
        'search_jobs',
        'jobs'
    ]
    
    print("=" * 80)
    print("Supabaseテーブルのスキーマ情報")
    print("=" * 80)
    
    for table_name in tables_to_check:
        print(f"\n【{table_name}テーブル】")
        print("-" * 40)
        
        try:
            # 1行だけ取得してカラム情報を確認
            result = supabase.table(table_name).select('*').limit(1).execute()
            
            if result.data and len(result.data) > 0:
                # データが存在する場合
                row = result.data[0]
                print("カラム名とサンプル値:")
                for key, value in row.items():
                    value_type = type(value).__name__
                    print(f"  - {key}: {value_type} (例: {str(value)[:50]}...)")
            else:
                # データが存在しない場合でも、テーブル構造は確認できる
                print("データなし（テーブルは存在）")
                # 空のINSERTを試みてエラーメッセージから構造を推測
                try:
                    supabase.table(table_name).insert({}).execute()
                except Exception as e:
                    error_msg = str(e)
                    if "null value in column" in error_msg:
                        print("必須カラム情報（エラーメッセージから推測）:")
                        print(f"  {error_msg}")
                        
        except Exception as e:
            print(f"エラー: {str(e)}")
    
    # SQLで直接スキーマ情報を取得
    print("\n\n" + "=" * 80)
    print("SQL情報スキーマから取得した型情報")
    print("=" * 80)
    
    # 情報スキーマクエリ
    schema_query = """
    SELECT 
        table_name,
        column_name,
        data_type,
        is_nullable,
        column_default
    FROM information_schema.columns
    WHERE table_schema = 'public' 
    AND table_name IN ('profiles', 'clients', 'job_requirements', 'candidates', 'search_jobs', 'jobs')
    ORDER BY table_name, ordinal_position;
    """
    
    try:
        # Supabase SQLエディタで実行するためのクエリを出力
        print("\n以下のクエリをSupabase SQLエディタで実行してください:")
        print("-" * 80)
        print(schema_query)
        print("-" * 80)
        
    except Exception as e:
        print(f"エラー: {str(e)}")

if __name__ == "__main__":
    get_table_schema_info()