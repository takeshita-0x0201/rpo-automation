#!/usr/bin/env python3
"""
ai_evaluationsテーブルとAIマッチング評価システムの現状調査スクリプト
"""
import os
from dotenv import load_dotenv

load_dotenv()

def investigate_ai_evaluations_table():
    """ai_evaluationsテーブルの現状を調査"""
    try:
        from core.utils.supabase_client import get_supabase_client
        supabase = get_supabase_client()
        
        print("=== ai_evaluationsテーブル構造調査 ===")
        
        # テーブルの存在確認
        try:
            # テーブルにアクセスしてみる
            test_response = supabase.table('ai_evaluations').select('*').limit(1).execute()
            print("✓ ai_evaluationsテーブルは存在します")
            
            # データ件数を確認
            count_response = supabase.table('ai_evaluations').select('*', count='exact').execute()
            data_count = count_response.count if count_response.count is not None else 0
            print(f"  データ件数: {data_count}件")
            
            # サンプルデータを確認
            if test_response.data:
                sample = test_response.data[0]
                print(f"  サンプルデータのカラム: {list(sample.keys())}")
                
                # 各カラムの値の例
                for key, value in sample.items():
                    if value is not None:
                        value_str = str(value)[:50] + "..." if len(str(value)) > 50 else str(value)
                        print(f"    {key}: {value_str}")
            else:
                print("  データが存在しません")
                
        except Exception as e:
            print(f"✗ ai_evaluationsテーブルアクセスエラー: {e}")
            return False
            
        return True
        
    except Exception as e:
        print(f"✗ データベース接続エラー: {e}")
        return False

def analyze_ai_matching_service():
    """AIマッチングサービスの処理内容を分析"""
    print("\n=== AIマッチングサービス分析 ===")
    
    try:
        from webapp.services.ai_matching_service import ai_matching_service
        
        print("✓ AIマッチングサービスの初期化成功")
        print(f"  マッチャー利用可能: {'Yes' if ai_matching_service.matcher else 'No (ダミーモード)'}")
        
        # ダミー結果の構造を確認
        dummy_result = ai_matching_service._generate_dummy_result()
        print(f"  ダミー結果の構造:")
        for key, value in dummy_result.items():
            print(f"    {key}: {type(value).__name__}")
            if isinstance(value, dict):
                for sub_key in value.keys():
                    print(f"      {sub_key}: {type(value[sub_key]).__name__}")
        
        return True
        
    except Exception as e:
        print(f"✗ AIマッチングサービス分析エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_table_schema():
    """テーブルスキーマの詳細確認"""
    print("\n=== テーブルスキーマ詳細確認 ===")
    
    try:
        from core.utils.supabase_client import get_supabase_client
        supabase = get_supabase_client()
        
        # PostgreSQLのinformation_schemaを使ってカラム情報を取得
        schema_query = """
        SELECT 
            column_name,
            data_type,
            is_nullable,
            column_default,
            character_maximum_length
        FROM information_schema.columns
        WHERE table_schema = 'public' 
        AND table_name = 'ai_evaluations'
        ORDER BY ordinal_position;
        """
        
        # RPC経由でクエリを実行（直接SQLは実行できないため、代替手段を使用）
        try:
            # まず既存のデータから推測
            response = supabase.table('ai_evaluations').select('*').limit(1).execute()
            if response.data:
                sample = response.data[0]
                print("現在のテーブル構造（データから推測）:")
                for column, value in sample.items():
                    value_type = type(value).__name__ if value is not None else "None"
                    print(f"  {column}: {value_type}")
            else:
                print("データが存在しないため、構造を推測できません")
                
        except Exception as e:
            print(f"スキーマ確認エラー: {e}")
        
    except Exception as e:
        print(f"✗ スキーマ確認エラー: {e}")

def identify_missing_requirements():
    """不足している要件を特定"""
    print("\n=== 不足要件の特定 ===")
    
    # AIマッチングサービスが期待するデータ構造
    expected_columns = {
        'id': 'UUID (Primary Key)',
        'search_id': 'TEXT (Job ID)',
        'candidate_id': 'UUID (Foreign Key to candidates)',
        'requirement_id': 'UUID (Foreign Key to job_requirements)',
        'ai_score': 'FLOAT (0-100)',
        'match_score': 'FLOAT (0-100)',
        'recommendation': 'TEXT (A/B/C/D)',
        'confidence': 'TEXT (High/Medium/Low)',
        'evaluation_result': 'JSONB (詳細評価結果)',
        'evaluated_at': 'TIMESTAMPTZ',
        'model_version': 'TEXT (Optional)',
        'prompt_version': 'TEXT (Optional)'
    }
    
    print("AIマッチングサービスが期待するテーブル構造:")
    for column, description in expected_columns.items():
        print(f"  {column}: {description}")
    
    # 実際のテーブル構造と比較
    try:
        from core.utils.supabase_client import get_supabase_client
        supabase = get_supabase_client()
        
        response = supabase.table('ai_evaluations').select('*').limit(1).execute()
        if response.data:
            actual_columns = set(response.data[0].keys())
            expected_columns_set = set(expected_columns.keys())
            
            missing_columns = expected_columns_set - actual_columns
            extra_columns = actual_columns - expected_columns_set
            
            if missing_columns:
                print(f"\n不足しているカラム: {missing_columns}")
            
            if extra_columns:
                print(f"余分なカラム: {extra_columns}")
                
            if not missing_columns and not extra_columns:
                print("\n✓ テーブル構造は期待通りです")
        
    except Exception as e:
        print(f"比較エラー: {e}")

if __name__ == "__main__":
    print("ai_evaluationsテーブルとAIマッチング評価システムの現状調査")
    print("=" * 70)
    
    # 1. テーブル構造調査
    table_exists = investigate_ai_evaluations_table()
    
    # 2. AIマッチングサービス分析
    service_ok = analyze_ai_matching_service()
    
    # 3. テーブルスキーマ詳細確認
    if table_exists:
        check_table_schema()
    
    # 4. 不足要件の特定
    identify_missing_requirements()
    
    print("\n" + "=" * 70)
    print("調査完了")