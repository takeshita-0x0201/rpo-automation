#!/usr/bin/env python3
"""
インタラクティブに求人情報とレジュメを入力して類似ケースを検索するスクリプト
"""

import os
import sys
import json
import tempfile
from pathlib import Path

# プロジェクトのルートパスを追加
sys.path.append(str(Path(__file__).parent.parent))

from scripts.search_similar_cases import SimilarCaseSearcher


def get_multiline_input(prompt):
    """複数行の入力を受け取る"""
    print(prompt)
    print("（入力終了は空行を2回入力）")
    
    lines = []
    empty_line_count = 0
    
    while True:
        line = input()
        if line == "":
            empty_line_count += 1
            if empty_line_count >= 2:
                break
            lines.append("")
        else:
            empty_line_count = 0
            lines.append(line)
    
    return "\n".join(lines[:-1])  # 最後の空行を除外


def main():
    print("=== 類似ケース検索システム ===\n")
    
    # APIキーの確認
    gemini_api_key = os.getenv('GEMINI_API_KEY')
    pinecone_api_key = os.getenv('PINECONE_API_KEY')
    
    if not gemini_api_key or not pinecone_api_key:
        print("エラー: GEMINI_API_KEYとPINECONE_API_KEY環境変数を設定してください")
        return
    
    # 求人票の入力
    print("\n【求人票を入力してください】")
    job_description = get_multiline_input("求人内容を入力:")
    
    # 求人メモの入力
    print("\n【求人メモを入力してください】")
    job_memo = get_multiline_input("求人の詳細要件やメモを入力:")
    
    # レジュメの入力
    print("\n【候補者のレジュメを入力してください】")
    resume = get_multiline_input("候補者の経歴・スキルを入力:")
    
    # 入力内容の確認
    print("\n=== 入力内容の確認 ===")
    print(f"\n求人票の文字数: {len(job_description)}文字")
    print(f"求人メモの文字数: {len(job_memo)}文字")
    print(f"レジュメの文字数: {len(resume)}文字")
    
    confirm = input("\nこの内容で検索を実行しますか？ (y/n): ")
    if confirm.lower() != 'y':
        print("キャンセルされました")
        return
    
    # 類似ケース検索を実行
    print("\n類似ケースを検索中...")
    searcher = SimilarCaseSearcher(gemini_api_key, pinecone_api_key)
    
    # 検索実行
    results = searcher.search_for_new_candidate(
        job_description,
        job_memo,
        resume
    )
    
    # 結果分析
    analysis = searcher.analyze_search_results(results)
    
    # 結果表示
    print_search_results(results, analysis)
    
    # 結果を保存
    save_results = input("\n結果をファイルに保存しますか？ (y/n): ")
    if save_results.lower() == 'y':
        output_data = {
            'input': {
                'job_description': job_description,
                'job_memo': job_memo,
                'resume': resume
            },
            'search_results': results,
            'analysis': analysis
        }
        
        output_file = 'interactive_search_result.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n結果を {output_file} に保存しました")


def print_search_results(results, analysis):
    """検索結果を表示（search_similar_cases.pyから流用）"""
    print("\n" + "="*60)
    print("類似ケース検索結果")
    print("="*60)
    
    # 総合的な類似ケース
    print("\n【最も類似したケース（総合）】")
    for i, case in enumerate(results.get('combined_matches', [])[:5], 1):
        print(f"\n{i}. 類似度: {case['score']:.3f}")
        print(f"   AI評価: {case['ai_recommendation']} / クライアント: {case['client_evaluation']}")
        print(f"   一致: {'○' if case['evaluation_match'] else '×'}")
        if case.get('client_comment'):
            print(f"   クライアントコメント: {case['client_comment']}")
    
    # 分析結果
    print("\n\n【分析結果】")
    
    print("\n1. クライアント評価の傾向")
    for eval, stats in analysis.get('client_evaluation_trends', {}).items():
        print(f"   {eval}: {stats['count']}件 ({stats['percentage']:.1f}%)")
    
    if analysis.get('risk_factors'):
        print("\n2. 注意すべきリスク要因")
        for risk in analysis['risk_factors']:
            print(f"   - AI:{risk['ai_evaluation']} → クライアント:{risk['client_evaluation']}")
            print(f"     理由: {risk['reason']}")
    
    print("\n3. 推奨アクション")
    trends = analysis.get('client_evaluation_trends', {})
    if 'D' in trends and trends['D']['percentage'] > 50:
        print("   ⚠️ 類似ケースの多くがNG判定です。要件の再確認を推奨します。")
    elif 'A' in trends and trends['A']['percentage'] > 30:
        print("   ✅ 類似ケースで高評価が多いです。積極的に推薦可能です。")


if __name__ == "__main__":
    main()