#!/usr/bin/env python3
"""
分離型DeepResearchマッチングの実行スクリプト
"""

import os
import sys
from ai_matching.nodes import SeparatedDeepResearchMatcher


def main():
    # APIキーの設定
    gemini_api_key = os.getenv('GEMINI_API_KEY')
    if not gemini_api_key:
        print("エラー: GEMINI_API_KEY環境変数が設定されていません")
        print("使用方法: export GEMINI_API_KEY='your-api-key'")
        sys.exit(1)
    
    tavily_api_key = os.getenv('TAVILY_API_KEY')
    if not tavily_api_key:
        print("警告: TAVILY_API_KEY環境変数が設定されていません")
        print("Tavily Web検索機能はシミュレーションモードで動作します")
        print("実際のWeb検索を使用する場合: export TAVILY_API_KEY='your-tavily-key'")
        print()
    
    # ファイルパス
    resume_file = 'sample_data/resume.txt'
    job_desc_file = 'sample_data/job_description.txt'
    job_memo_file = 'sample_data/job_memo.txt'
    
    # ファイルの存在確認
    for filepath in [resume_file, job_desc_file, job_memo_file]:
        if not os.path.exists(filepath):
            print(f"エラー: ファイルが見つかりません - {filepath}")
            sys.exit(1)
    
    print("\n" + "="*70)
    print("=== 分離型 DeepResearch 採用マッチング ===")
    print("="*70)
    print("各処理ノードが独立して動作します")
    print(f"Tavily検索: {'有効' if tavily_api_key else 'シミュレーションモード'}")
    print(f"処理対象ファイル:")
    print(f"  - レジュメ: {resume_file}")
    print(f"  - 求人票: {job_desc_file}")
    print(f"  - 求人メモ: {job_memo_file}")
    print("="*70)
    
    # マッチャー作成
    matcher = SeparatedDeepResearchMatcher(
        gemini_api_key=gemini_api_key,
        tavily_api_key=tavily_api_key
    )
    
    try:
        # マッチング実行
        result = matcher.match_candidate(
            resume_file,
            job_desc_file,
            job_memo_file,
            max_cycles=3
        )
        
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
        
        
        # プロセス統計
        print(f"\n【処理統計】")
        print(f"  評価サイクル: {result['total_cycles']}回")
        print(f"  Web検索実行: {result['total_searches']}回")
        print(f"  最終スコア: {result['final_score']}点")
        print(f"  最終確信度: {result['final_confidence']}")
        
        # 評価履歴
        print(f"\n【評価履歴】")
        for hist in result['evaluation_history']:
            print(f"  サイクル{hist['cycle']}: " +
                  f"スコア{hist['score']} ({hist['confidence']}) " +
                  f"- {hist['gaps_found']}件のギャップ、" +
                  f"{hist['searches_performed']}件の検索 " +
                  f"({hist['duration']}秒)")
        
        # 処理時間の合計
        total_time = sum(hist['duration'] for hist in result['evaluation_history'])
        print(f"\n総処理時間: {total_time:.2f}秒")
        
    except Exception as e:
        print(f"\nエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()