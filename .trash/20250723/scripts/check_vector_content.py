#!/usr/bin/env python3
"""
Edge Functionが生成しているベクトルテキストの内容を確認
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

# 同期済みの評価を1件取得
response = supabase.table('client_evaluations').select('*').eq('synced_to_pinecone', True).limit(1).execute()

if not response.data:
    print("同期済みのデータが見つかりません")
    exit()

evaluation = response.data[0]
print(f"対象評価: {evaluation['candidate_id']} - {evaluation['requirement_id']}")
print("-" * 80)

# 関連データを収集（Edge Functionと同じロジック）
# 候補者データ
candidates = supabase.table('candidates').select('*').eq('candidate_id', evaluation['candidate_id']).execute()
candidate = candidates.data[0] if candidates.data else None

# 求人要件データ
requirements = supabase.table('job_requirements').select('*, clients(*)').eq('requirement_id', evaluation['requirement_id']).execute()
requirement = requirements.data[0] if requirements.data else None

# AI評価データ
if candidate and requirement:
    ai_evaluations = supabase.table('ai_evaluations').select('*').eq('candidate_id', candidate['id']).eq('requirement_id', requirement['id']).execute()
    ai_evaluation = ai_evaluations.data[0] if ai_evaluations.data else None
else:
    ai_evaluation = None

# データの存在確認
print("\n【データ存在確認】")
print(f"候補者データ: {'✓' if candidate else '✗'}")
print(f"求人要件データ: {'✓' if requirement else '✗'}")
print(f"AI評価データ: {'✓' if ai_evaluation else '✗'}")

if ai_evaluation:
    print(f"  - AIスコア: {ai_evaluation.get('ai_score', 'なし')}")
    print(f"  - 推奨度: {ai_evaluation.get('recommendation', 'なし')}")

# ベクトルテキストを生成（Edge Functionと同じロジック）
print("\n【生成されるベクトルテキスト】")
print("\n1. 求人側ベクトル:")
print("-" * 40)

if requirement:
    client = requirement.get('clients', {})
    job_side_text = f"""ポジション: {requirement.get('title', '')}
クライアント: {client.get('name', '') if client else ''}

求人詳細:
{requirement.get('job_description', '')}

求人メモ:
{requirement.get('memo', '')}"""
    print(job_side_text[:500] + "..." if len(job_side_text) > 500 else job_side_text)
else:
    print("求人データなし")

print("\n2. 候補者ベクトル:")
print("-" * 40)

if candidate:
    candidate_text = f"""候補者: {candidate.get('candidate_id', '')}
所属企業: {candidate.get('candidate_company', '')}

レジュメ:
{candidate.get('candidate_resume', '')}

AI評価スコア: {ai_evaluation.get('ai_score', 'N/A') if ai_evaluation else 'N/A'}
推奨度: {ai_evaluation.get('recommendation', 'N/A') if ai_evaluation else 'N/A'}

強み:
{', '.join(ai_evaluation.get('strengths', [])) if ai_evaluation and ai_evaluation.get('strengths') else ''}

懸念点:
{', '.join(ai_evaluation.get('concerns', [])) if ai_evaluation and ai_evaluation.get('concerns') else ''}

クライアント評価: {evaluation.get('client_evaluation', '')}
評価者: {evaluation.get('created_by', '')}
フィードバック: {evaluation.get('client_feedback', '')}"""
    print(candidate_text[:500] + "..." if len(candidate_text) > 500 else candidate_text)
else:
    print("候補者データなし")

# データ品質の分析
print("\n\n【データ品質分析】")
issues = []

if not candidate or not candidate.get('candidate_resume'):
    issues.append("候補者レジュメが空または存在しない")

if not requirement or not requirement.get('job_description'):
    issues.append("求人詳細が空または存在しない")

if not ai_evaluation:
    issues.append("AI評価が存在しない")
elif not ai_evaluation.get('ai_score'):
    issues.append("AIスコアが存在しない")

if issues:
    print("問題点:")
    for issue in issues:
        print(f"  ⚠️  {issue}")
else:
    print("✓ データ品質に問題なし")

# 推奨事項
print("\n【推奨事項】")
print("1. AI評価データが存在しない場合は、事前にAI評価を実行する必要があります")
print("2. 候補者レジュメと求人詳細は、ベクトル化の品質に直結するため必須です")
print("3. AIスコアは検索時のフィルタリングに使用されるため、適切に設定されている必要があります")