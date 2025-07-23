#!/usr/bin/env python3
"""
DeepResearchマッチングの実行スクリプト
"""

import os
import sys
from ai_matching.deep_research_matcher import DeepResearchMatcher

def main():
    # Gemini APIキーの設定
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("エラー: GEMINI_API_KEY環境変数が設定されていません")
        print("使用方法: export GEMINI_API_KEY='your-api-key'")
        sys.exit(1)
    
    # ファイルパス（固定のデフォルトファイルを使用）
    resume_file = 'sample_data/resume.txt'
    job_desc_file = 'sample_data/job_description.txt'
    job_memo_file = 'sample_data/job_memo.txt'
    
    # ファイルの存在確認
    for filepath in [resume_file, job_desc_file, job_memo_file]:
        if not os.path.exists(filepath):
            print(f"エラー: ファイルが見つかりません - {filepath}")
            sys.exit(1)
    
    print("=== DeepResearch 採用マッチング開始 ===\n")
    
    # マッチャー作成
    matcher = DeepResearchMatcher(api_key, max_cycles=3)
    
    try:
        # マッチング実行
        result = matcher.match_candidate(resume_file, job_desc_file, job_memo_file)
        
        # 結果表示
        print("\n" + "="*70)
        print("=== 最終マッチング結果 ===")
        print("="*70)
        
        final = result['final_judgment']
        print(f"\n【推奨度】 {final['recommendation']}")
        
        print(f"\n【強み】")
        for s in final['strengths']:
            print(f"  ✓ {s}")
            
        print(f"\n【懸念点】")
        for c in final['concerns']:
            print(f"  ⚠ {c}")
            
        print(f"\n【総合評価】")
        print(f"  {final['overall_assessment']}")
        
        print(f"\n【面接確認事項】")
        for i, p in enumerate(final['interview_points'], 1):
            print(f"  {i}. {p}")
        
        print(f"\n評価サイクル数: {result['total_cycles']}回")
        
    except Exception as e:
        print(f"\nエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()