#!/usr/bin/env python3
"""
LLMレスポンスの詳細分析スクリプト
raw_responseから実際のLLM出力を確認する
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

def analyze_llm_responses():
    """LLMの実際のレスポンスを分析"""
    supabase = get_supabase_client()
    
    # 最新の評価を取得（overall_assessmentがプレースホルダーのもの）
    response = supabase.table('ai_evaluations').select('*').eq('overall_assessment', '総合的な評価を実施中').order('evaluated_at', desc=True).limit(5).execute()
    evaluations = response.data or []
    
    print(f"分析対象: {len(evaluations)}件のプレースホルダー評価\n")
    
    for i, eval in enumerate(evaluations, 1):
        print(f"\n{'='*70}")
        print(f"評価 {i}")
        print(f"{'='*70}")
        print(f"ID: {eval['id']}")
        print(f"評価日時: {eval['evaluated_at']}")
        print(f"推奨度: {eval.get('recommendation', 'N/A')}")
        print(f"overall_assessment: {eval.get('overall_assessment', '')}")
        
        raw_response = eval.get('raw_response')
        if raw_response:
            try:
                response_data = json.loads(raw_response)
                
                # evaluation_historyから最後の評価サイクルを取得
                eval_history = response_data.get('evaluation_history', [])
                if eval_history:
                    last_cycle = eval_history[-1]
                    print(f"\n最終サイクル情報:")
                    print(f"  サイクル: {last_cycle.get('cycle')}")
                    print(f"  スコア: {last_cycle.get('score')}")
                    print(f"  確信度: {last_cycle.get('confidence')}")
                
                # final_judgmentの内容を確認
                final_judgment = response_data.get('final_judgment', {})
                print(f"\nfinal_judgment内容:")
                print(f"  recommendation: {final_judgment.get('recommendation')}")
                print(f"  reason: {final_judgment.get('reason', '')[:100]}...")
                print(f"  overall_assessment: {final_judgment.get('overall_assessment', '')}")
                
                # 実際にLLMに送られたプロンプトの一部を推測
                print(f"\n評価に使用された情報:")
                print(f"  総サイクル数: {response_data.get('total_cycles', 0)}")
                print(f"  総検索数: {response_data.get('total_searches', 0)}")
                
            except json.JSONDecodeError as e:
                print(f"JSONパースエラー: {e}")
        else:
            print("raw_responseが空です")

def check_llm_output_format():
    """実際のLLM出力フォーマットを確認"""
    print("\n\n" + "="*70)
    print("LLM出力フォーマットの確認")
    print("="*70)
    
    supabase = get_supabase_client()
    
    # overall_assessmentが正常に取得できている評価を確認
    response = supabase.table('ai_evaluations').select('*').neq('overall_assessment', '総合的な評価を実施中').neq('overall_assessment', '').order('evaluated_at', desc=True).limit(3).execute()
    evaluations = response.data or []
    
    print(f"\n正常に取得できている評価: {len(evaluations)}件\n")
    
    for i, eval in enumerate(evaluations, 1):
        print(f"\n--- 正常な評価 {i} ---")
        print(f"overall_assessment: {eval.get('overall_assessment', '')[:100]}...")
        
        raw_response = eval.get('raw_response')
        if raw_response:
            try:
                response_data = json.loads(raw_response)
                final_judgment = response_data.get('final_judgment', {})
                
                # 各フィールドの存在を確認
                print(f"final_judgmentのキー: {list(final_judgment.keys())}")
                
            except json.JSONDecodeError:
                pass

if __name__ == '__main__':
    analyze_llm_responses()
    check_llm_output_format()