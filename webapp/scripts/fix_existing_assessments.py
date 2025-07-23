#!/usr/bin/env python3
"""
既存のプレースホルダー評価を修正するスクリプト
"""
import os
import sys
import json
from datetime import datetime

# プロジェクトのルートディレクトリをPythonパスに追加
current_dir = os.path.dirname(os.path.abspath(__file__))
webapp_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(webapp_dir)
sys.path.append(project_root)

from core.utils.supabase_client import get_supabase_client

def generate_assessment_from_data(recommendation: str, reason: str, strengths: list, concerns: list) -> str:
    """既存データから総合評価を生成"""
    if not reason:
        return "詳細な評価結果については、強みと懸念点をご確認ください。"
    
    # reasonの最初の部分を使用
    assessment = f"候補者は{reason} "
    
    # recommendationに基づいて結論を追加
    if recommendation == 'A':
        assessment += "以上の経験・スキルから、本ポジションに非常に適した人材と判断します。"
        if strengths and len(strengths) > 0:
            assessment += f"特に{strengths[0]}は高く評価できます。"
    elif recommendation == 'B':
        assessment += "必要な要件を概ね満たしており、本ポジションでの活躍が期待できます。"
        if concerns and len(concerns) > 0:
            assessment += f"ただし、{concerns[0]}については面接で確認が必要です。"
    elif recommendation == 'C':
        assessment += "一定の要件は満たしているものの、面接での詳細確認が必要です。"
        if concerns and len(concerns) > 0:
            assessment += f"特に{concerns[0]}の点について慎重な検討が求められます。"
    else:  # D
        assessment += "現時点では必須要件との適合度が低いと判断します。"
        if concerns and len(concerns) > 0:
            assessment += f"{concerns[0]}という課題があり、今回の採用は見送りが妥当です。"
    
    return assessment

def fix_placeholder_assessments(dry_run=True):
    """プレースホルダーの評価を修正"""
    supabase = get_supabase_client()
    
    # プレースホルダーの評価を取得
    response = supabase.table('ai_evaluations').select('*').eq('overall_assessment', '総合的な評価を実施中').execute()
    evaluations = response.data or []
    
    print(f"修正対象: {len(evaluations)}件のプレースホルダー評価\n")
    
    fixed_count = 0
    error_count = 0
    
    for eval in evaluations:
        eval_id = eval['id']
        
        try:
            # raw_responseから情報を取得
            raw_response = eval.get('raw_response')
            if not raw_response:
                print(f"[SKIP] ID {eval_id}: raw_responseが空")
                continue
            
            response_data = json.loads(raw_response)
            final_judgment = response_data.get('final_judgment', {})
            
            # 必要なデータを取得
            recommendation = eval.get('recommendation', final_judgment.get('recommendation', 'C'))
            reason = final_judgment.get('reason', '')
            strengths = eval.get('strengths', final_judgment.get('strengths', []))
            concerns = eval.get('concerns', final_judgment.get('concerns', []))
            
            # 新しい総合評価を生成
            new_assessment = generate_assessment_from_data(recommendation, reason, strengths, concerns)
            
            print(f"[FIX] ID {eval_id}:")
            print(f"  推奨度: {recommendation}")
            print(f"  理由: {reason[:50]}...")
            print(f"  新しい評価: {new_assessment[:80]}...")
            
            if not dry_run:
                # データベースを更新
                update_result = supabase.table('ai_evaluations').update({
                    'overall_assessment': new_assessment,
                    'updated_at': datetime.utcnow().isoformat()
                }).eq('id', eval_id).execute()
                
                if update_result.data:
                    fixed_count += 1
                    print(f"  → 更新成功")
                else:
                    error_count += 1
                    print(f"  → 更新失敗")
            else:
                fixed_count += 1
                print(f"  → [DRY RUN] 更新をスキップ")
            
            print()
            
        except Exception as e:
            error_count += 1
            print(f"[ERROR] ID {eval_id}: {e}\n")
    
    print(f"\n=== 結果 ===")
    print(f"修正対象: {len(evaluations)}件")
    print(f"修正成功: {fixed_count}件")
    print(f"エラー: {error_count}件")
    
    if dry_run:
        print("\n※ DRY RUNモードで実行しました。実際の更新は行われていません。")
        print("実際に更新する場合は、--executeオプションを指定してください。")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='既存のプレースホルダー評価を修正')
    parser.add_argument('--execute', action='store_true', help='実際にデータベースを更新する')
    args = parser.parse_args()
    
    fix_placeholder_assessments(dry_run=not args.execute)