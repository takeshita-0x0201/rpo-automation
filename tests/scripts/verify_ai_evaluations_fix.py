#!/usr/bin/env python3
"""
ai_evaluationsテーブル修正後の確認スクリプト
"""
import os
from dotenv import load_dotenv

load_dotenv()

def verify_table_structure():
    """テーブル構造の確認"""
    try:
        from core.utils.supabase_client import get_supabase_client
        supabase = get_supabase_client()
        
        print("=== ai_evaluationsテーブル構造確認 ===")
        
        # テーブルアクセステスト
        try:
            response = supabase.table('ai_evaluations').select('*').limit(1).execute()
            print("✓ テーブルアクセス成功")
            
            # データ件数確認
            count_response = supabase.table('ai_evaluations').select('*', count='exact').execute()
            print(f"  データ件数: {count_response.count}件")
            
        except Exception as e:
            print(f"✗ テーブルアクセスエラー: {e}")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ 確認エラー: {e}")
        return False

def test_ai_matching_integration():
    """AIマッチングサービスとの統合テスト"""
    print("\n=== AIマッチングサービス統合テスト ===")
    
    try:
        from webapp.services.ai_matching_service import ai_matching_service
        from core.utils.supabase_client import get_supabase_client
        import uuid
        from datetime import datetime
        
        supabase = get_supabase_client()
        
        # テスト用の評価データを作成
        test_candidate = {
            'id': str(uuid.uuid4()),
            'requirement_id': None  # NULLでテスト
        }
        
        test_result = ai_matching_service._generate_dummy_result()
        test_job_id = "test-integration-" + str(int(datetime.now().timestamp()))
        
        print("テスト用評価データ保存...")
        
        # 評価結果保存のテスト
        try:
            await ai_matching_service._save_evaluation_result(test_job_id, test_candidate, test_result)
            print("✓ 評価結果保存成功")
            
            # 保存されたデータを確認
            saved_response = supabase.table('ai_evaluations').select('*').eq('search_id', test_job_id).execute()
            if saved_response.data:
                saved_data = saved_response.data[0]
                print(f"  保存されたデータ:")
                print(f"    ID: {saved_data['id']}")
                print(f"    スコア: {saved_data['ai_score']}")
                print(f"    推奨度: {saved_data['recommendation']}")
                print(f"    確信度: {saved_data['confidence']}")
                
                # テストデータを削除
                supabase.table('ai_evaluations').delete().eq('id', saved_data['id']).execute()
                print("  テストデータを削除しました")
                
            return True
            
        except Exception as e:
            print(f"✗ 評価結果保存エラー: {e}")
            return False
        
    except Exception as e:
        print(f"✗ 統合テストエラー: {e}")
        import traceback
        traceback.print_exc()
        return False

async def run_verification():
    """非同期で確認を実行"""
    # 1. テーブル構造確認
    table_ok = verify_table_structure()
    
    # 2. 統合テスト
    if table_ok:
        integration_ok = await test_ai_matching_integration()
        
        if integration_ok:
            print("\n✓ すべての確認が完了しました")
            print("ai_evaluationsテーブルとAIマッチングサービスの統合が正常に動作します")
        else:
            print("\n✗ 統合テストに失敗しました")
    else:
        print("\n✗ テーブル構造に問題があります")

if __name__ == "__main__":
    import asyncio
    
    print("ai_evaluationsテーブル修正後の確認")
    print("=" * 50)
    
    asyncio.run(run_verification())