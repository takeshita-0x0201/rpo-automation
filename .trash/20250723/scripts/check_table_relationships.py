#!/usr/bin/env python3
"""
テーブル間のリレーションシップを確認
"""
import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

# Supabase設定
SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://agpoeoexuirxzdszdtlu.supabase.co')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')

# Supabaseクライアントを作成
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

print("=== 1. client_evaluationsテーブルのサンプル ===")
ce_response = supabase.table('client_evaluations').select('candidate_id, requirement_id, client_evaluation, synced_to_pinecone').eq('synced_to_pinecone', True).limit(3).execute()
for row in ce_response.data:
    print(f"candidate_id: {row['candidate_id']}, requirement_id: {row['requirement_id']}, evaluation: {row['client_evaluation']}")

print("\n=== 2. candidatesテーブルの構造確認 ===")
# 同期済みのcandidate_idを取得
synced_candidates = [row['candidate_id'] for row in ce_response.data]
if synced_candidates:
    c_response = supabase.table('candidates').select('id, candidate_id, candidate_company').in_('candidate_id', synced_candidates).execute()
    for row in c_response.data:
        print(f"id(UUID): {row['id']}, candidate_id(TEXT): {row['candidate_id']}, company: {row['candidate_company']}")

print("\n=== 3. job_requirementsテーブルの構造確認 ===")
# 同期済みのrequirement_idを取得
synced_requirements = [row['requirement_id'] for row in ce_response.data]
if synced_requirements:
    jr_response = supabase.table('job_requirements').select('id, requirement_id, title').in_('requirement_id', synced_requirements).execute()
    for row in jr_response.data:
        print(f"id(UUID): {row['id']}, requirement_id(TEXT): {row['requirement_id']}, title: {row['title']}")

print("\n=== 4. ai_evaluationsテーブルのサンプル ===")
ae_response = supabase.table('ai_evaluations').select('id, candidate_id, requirement_id, score, recommendation').limit(5).execute()
for row in ae_response.data:
    print(f"id: {row['id']}")
    print(f"  candidate_id: {row['candidate_id']} (type: {type(row['candidate_id']).__name__})")
    print(f"  requirement_id: {row['requirement_id']} (type: {type(row['requirement_id']).__name__})")
    print(f"  score: {row.get('score', 'NULL')}, recommendation: {row.get('recommendation', 'NULL')}")

print("\n=== 5. 結合テスト ===")
# 1件ずつ結合を確認
if ce_response.data:
    ce = ce_response.data[0]
    print(f"テスト対象: {ce['candidate_id']} - {ce['requirement_id']}")
    
    # 候補者を検索
    candidate = supabase.table('candidates').select('*').eq('candidate_id', ce['candidate_id']).execute()
    if candidate.data:
        c = candidate.data[0]
        print(f"候補者UUID: {c['id']}")
        
        # 求人を検索
        requirement = supabase.table('job_requirements').select('*').eq('requirement_id', ce['requirement_id']).execute()
        if requirement.data:
            r = requirement.data[0]
            print(f"求人UUID: {r['id']}")
            
            # AI評価を検索（UUID使用）
            ai_eval_uuid = supabase.table('ai_evaluations').select('*').eq('candidate_id', c['id']).eq('requirement_id', r['id']).execute()
            print(f"\nUUIDでのAI評価検索結果: {len(ai_eval_uuid.data)}件")
            if ai_eval_uuid.data:
                print(f"  スコア: {ai_eval_uuid.data[0].get('score', 'NULL')}")
            
            # AI評価を検索（TEXT ID使用）
            ai_eval_text = supabase.table('ai_evaluations').select('*').eq('candidate_id', ce['candidate_id']).eq('requirement_id', ce['requirement_id']).execute()
            print(f"TEXT IDでのAI評価検索結果: {len(ai_eval_text.data)}件")
            if ai_eval_text.data:
                print(f"  スコア: {ai_eval_text.data[0].get('score', 'NULL')}")

print("\n=== 推論 ===")
print("ai_evaluationsテーブルのcandidate_idとrequirement_idのデータ型を確認して、")
print("Edge Functionでの結合条件を適切に修正する必要があります。")