#!/usr/bin/env python3
"""
ジョブを手動で実行して問題を特定
"""
import asyncio
import os
import sys
from dotenv import load_dotenv

# 環境変数を読み込み
load_dotenv()

# パスを追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def execute_job_manually():
    """ジョブを手動実行"""
    
    from webapp.services.ai_matching_service import ai_matching_service
    from core.utils.supabase_client import get_supabase_client
    
    # pendingのジョブIDを使用
    job_id = "94e5c888-5f53-4187-b905-7e2b08416874"
    
    print(f"=== ジョブ手動実行 ===")
    print(f"Job ID: {job_id}\n")
    
    try:
        # process_jobメソッドを呼び出す前に、現在の状態を確認
        supabase = get_supabase_client()
        job_before = supabase.table('jobs').select('status').eq('id', job_id).single().execute()
        print(f"実行前のステータス: {job_before.data['status']}")
        
        # 実際のジョブ処理を実行（1候補者のみテスト）
        await ai_matching_service.process_job(job_id)
        
        # 実行後の状態を確認
        job_after = supabase.table('jobs').select('status').eq('id', job_id).single().execute()
        print(f"\n実行後のステータス: {job_after.data['status']}")
        
        # 作成された評価を確認
        evals = supabase.table('ai_evaluations').select('id, ai_score, recommendation').eq('search_id', job_id).limit(5).execute()
        print(f"\n作成された評価: {len(evals.data)}件")
        for eval in evals.data:
            print(f"  - Score: {eval['ai_score']}, Rec: {eval['recommendation']}")
            
    except Exception as e:
        print(f"\nエラー発生: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # 注意: これは実際にジョブを実行します
    print("警告: このスクリプトは実際のジョブを実行します。")
    response = input("続行しますか？ (y/N): ")
    
    if response.lower() == 'y':
        asyncio.run(execute_job_manually())
    else:
        print("キャンセルされました。")