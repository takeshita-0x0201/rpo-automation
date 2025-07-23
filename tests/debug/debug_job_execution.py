#!/usr/bin/env python3
"""
ジョブ実行のデバッグスクリプト
"""
import os
import sys
from dotenv import load_dotenv

# 環境変数を読み込み
load_dotenv()

def check_environment():
    """環境変数をチェック"""
    print("=== 環境変数チェック ===")
    required_vars = [
        'SUPABASE_URL',
        'SUPABASE_ANON_KEY',
        'SUPABASE_SERVICE_KEY',
        'GEMINI_API_KEY'
    ]
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"✓ {var}: {'*' * min(len(value), 10)}...")
        else:
            print(f"✗ {var}: 未設定")

def test_supabase_connection():
    """Supabase接続をテスト"""
    print("\n=== Supabase接続テスト ===")
    try:
        from core.utils.supabase_client import get_supabase_client
        supabase = get_supabase_client()
        
        # テーブル一覧を取得
        result = supabase.table('jobs').select('id').limit(1).execute()
        print(f"✓ Supabase接続成功: {len(result.data) if result.data else 0}件のジョブが見つかりました")
        
    except Exception as e:
        print(f"✗ Supabase接続エラー: {e}")

def test_ai_matching_service():
    """AIマッチングサービスをテスト"""
    print("\n=== AIマッチングサービステスト ===")
    try:
        from webapp.services.ai_matching_service import ai_matching_service
        print(f"✓ AIマッチングサービス初期化成功")
        print(f"  - マッチャー: {'利用可能' if ai_matching_service.matcher else '利用不可（ダミーモード）'}")
        
    except Exception as e:
        print(f"✗ AIマッチングサービスエラー: {e}")
        import traceback
        traceback.print_exc()

def test_job_creation():
    """テスト用ジョブの作成"""
    print("\n=== テストジョブ作成 ===")
    try:
        from core.utils.supabase_client import get_supabase_client
        import uuid
        from datetime import datetime
        
        supabase = get_supabase_client()
        
        # テスト用ジョブデータ
        job_data = {
            "id": str(uuid.uuid4()),
            "job_id": "test-job-001",
            "job_type": "ai_matching",
            "name": "テストジョブ",
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
            "parameters": {
                "data_source": "latest",
                "matching_threshold": "high"
            }
        }
        
        # ジョブを作成（実際には作成しない、バリデーションのみ）
        print(f"✓ テストジョブデータ作成成功: {job_data['job_id']}")
        
    except Exception as e:
        print(f"✗ テストジョブ作成エラー: {e}")

if __name__ == "__main__":
    print("ジョブ実行デバッグスクリプト")
    print("=" * 50)
    
    check_environment()
    test_supabase_connection()
    test_ai_matching_service()
    test_job_creation()
    
    print("\n=== デバッグ完了 ===")