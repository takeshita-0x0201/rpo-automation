#!/usr/bin/env python3
"""
AIマッチング実行のデバッグ
実際の処理フローを追跡
"""
import asyncio
import os
import sys
from dotenv import load_dotenv

# 環境変数を読み込み
load_dotenv()

# パスを追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def debug_matching_execution():
    """マッチング実行をデバッグ"""
    
    from webapp.services.ai_matching_service import ai_matching_service
    from core.utils.supabase_client import get_supabase_client
    
    supabase = get_supabase_client()
    
    # テスト用のジョブIDを使用（実際の pending ジョブ）
    job_id = "94e5c888-5f53-4187-b905-7e2b08416874"
    
    print(f"=== AIマッチング実行デバッグ ===")
    print(f"Job ID: {job_id}\n")
    
    # ジョブ詳細を取得
    job = await ai_matching_service._get_job_details(job_id)
    print(f"1. ジョブ詳細:")
    print(f"   - Status: {job['status']}")
    print(f"   - Requirement ID: {job.get('requirement_id')}")
    print(f"   - Client ID: {job.get('client_id')}")
    
    # 要件情報を取得
    requirement = await ai_matching_service._get_requirement(job['requirement_id'])
    print(f"\n2. 要件情報:")
    print(f"   - Title: {requirement.get('title')}")
    print(f"   - Description: {requirement.get('description', '')[:50]}...")
    
    # 候補者を取得
    candidates = await ai_matching_service._get_candidates_for_job(job)
    print(f"\n3. 候補者情報:")
    print(f"   - 取得数: {len(candidates)}")
    
    if candidates:
        # 最初の候補者で詳細テスト
        candidate = candidates[0]
        print(f"\n4. 最初の候補者でテスト:")
        print(f"   - ID: {candidate['id']}")
        print(f"   - Company: {candidate.get('candidate_company')}")
        print(f"   - Resume length: {len(candidate.get('candidate_resume', ''))} chars")
        
        # レジュメの内容を確認
        resume_text = candidate.get('candidate_resume', '')
        print(f"   - Resume preview: {resume_text[:100]}..." if resume_text else "   - Resume: EMPTY!")
        
        # マッチャーの状態を再確認
        print(f"\n5. マッチャー状態:")
        print(f"   - ai_matching_service.matcher: {ai_matching_service.matcher}")
        print(f"   - hasattr match_candidate_direct: {hasattr(ai_matching_service.matcher, 'match_candidate_direct') if ai_matching_service.matcher else 'N/A'}")
        
        # 条件チェックを詳細に
        condition = ai_matching_service.matcher and hasattr(ai_matching_service.matcher, 'match_candidate_direct')
        print(f"   - Condition result: {condition}")
        
        # フォーマットされたテキストを確認
        job_desc_text = ai_matching_service._format_job_description(requirement)
        job_memo_text = ai_matching_service._format_job_memo(requirement)
        
        print(f"\n6. フォーマット済みテキスト:")
        print(f"   - Job description length: {len(job_desc_text)} chars")
        print(f"   - Job memo length: {len(job_memo_text)} chars")
        
        # 実際のマッチング条件をテスト
        if condition:
            print(f"\n7. 実際のマッチングを実行（テスト）:")
            try:
                result = await asyncio.to_thread(
                    ai_matching_service.matcher.match_candidate_direct,
                    resume_text=resume_text,
                    job_description_text=job_desc_text,
                    job_memo_text=job_memo_text,
                    max_cycles=1
                )
                print(f"   - Result score: {result.get('final_score')}")
                print(f"   - Result recommendation: {result.get('final_judgment', {}).get('recommendation')}")
            except Exception as e:
                print(f"   - Error: {type(e).__name__}: {e}")
        else:
            print(f"\n7. マッチャー条件がFalseのため、ダミー結果が使用されます")
            dummy = ai_matching_service._generate_dummy_result()
            print(f"   - Dummy score: {dummy['final_score']}")
            print(f"   - Dummy recommendation: {dummy['final_judgment']['recommendation']}")

if __name__ == "__main__":
    asyncio.run(debug_matching_execution())