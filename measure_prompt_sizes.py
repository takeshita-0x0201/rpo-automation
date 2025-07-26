#!/usr/bin/env python3
"""
Geminiのレート制限とコンテキストサイズ調査スクリプト
実際のプロンプトサイズと使用量を測定
"""

import os
import sys
from typing import Dict, List, Tuple

# プロジェクトパスを追加
sys.path.append(os.path.join(os.path.dirname(__file__), 'ai_matching_system'))

# プロンプトクラスをインポート
from ai_matching.prompts.evaluation_base import EvaluationPrompts
from ai_matching.prompts.scoring_criteria import ScoringCriteria
from ai_matching.prompts.requirement_rules import RequirementRules

def count_tokens_estimate(text: str) -> int:
    """
    トークン数の推定（日本語を考慮）
    - 英語: 約4文字 = 1トークン
    - 日本語: 約2文字 = 1トークン（漢字・ひらがな・カタカナ）
    """
    # 簡易的な推定
    japanese_chars = sum(1 for c in text if '\u3000' <= c <= '\u9fff' or '\u3040' <= c <= '\u309f' or '\u30a0' <= c <= '\u30ff')
    english_chars = len(text) - japanese_chars
    
    # 日本語は2文字で1トークン、英語は4文字で1トークン
    estimated_tokens = (japanese_chars / 2) + (english_chars / 4)
    return int(estimated_tokens)

def measure_prompt_sizes():
    """各プロンプトのサイズを測定"""
    
    # サンプルデータサイズ（実際のデータに基づく推定）
    sample_sizes = {
        "resume": 5000,  # 候補者レジュメ（5000文字程度）
        "job_description": 3000,  # 求人票（3000文字程度）
        "job_memo": 2000,  # 求人メモ（2000文字程度）
        "structured_job_data": 1500,  # 構造化求人データ
        "structured_resume_data": 1500,  # 構造化レジュメデータ
        "candidate_info": 200,  # 候補者基本情報
        "rag_insights": 1000,  # RAG検索結果
        "search_results": 2000,  # Web検索結果（1回あたり）
    }
    
    print("=== Gemini API レート制限とコンテキストサイズ調査 ===\n")
    
    print("## 1. 各ノードのプロンプトサイズ分析\n")
    
    # 1. 評価ノード（EvaluatorNode）のプロンプトサイズ
    print("### 評価ノード (EvaluatorNode)")
    evaluator_base = len(EvaluationPrompts.ROLE_SETTING) + len(EvaluationPrompts.EVALUATION_RULES) + len(EvaluationPrompts.SEMANTIC_UNDERSTANDING) + len(EvaluationPrompts.BALANCED_EVALUATION)
    evaluator_input = sum([sample_sizes["resume"], sample_sizes["job_description"], sample_sizes["job_memo"], 
                          sample_sizes["structured_job_data"], sample_sizes["structured_resume_data"], 
                          sample_sizes["candidate_info"]])
    evaluator_total_chars = evaluator_base + evaluator_input
    evaluator_tokens = count_tokens_estimate(" " * evaluator_total_chars)
    
    print(f"- ベースプロンプト: {evaluator_base:,} 文字")
    print(f"- 入力データ: {evaluator_input:,} 文字")
    print(f"- 合計: {evaluator_total_chars:,} 文字")
    print(f"- 推定トークン数: {evaluator_tokens:,} トークン\n")
    
    # 2. ギャップ分析ノード（GapAnalyzerNode）
    print("### ギャップ分析ノード (GapAnalyzerNode)")
    gap_analyzer_base = 1000  # プロンプトテンプレート推定
    gap_analyzer_input = 500  # 評価結果の要約
    gap_analyzer_total = gap_analyzer_base + gap_analyzer_input
    gap_analyzer_tokens = count_tokens_estimate(" " * gap_analyzer_total)
    
    print(f"- ベースプロンプト: {gap_analyzer_base:,} 文字")
    print(f"- 入力データ: {gap_analyzer_input:,} 文字") 
    print(f"- 合計: {gap_analyzer_total:,} 文字")
    print(f"- 推定トークン数: {gap_analyzer_tokens:,} トークン\n")
    
    # 3. 検索ノード（SearcherNode）
    print("### 検索ノード (SearcherNode)")
    searcher_base = 800  # プロンプトテンプレート推定
    searcher_input = sample_sizes["search_results"]
    searcher_total = searcher_base + searcher_input
    searcher_tokens = count_tokens_estimate(" " * searcher_total)
    
    print(f"- ベースプロンプト: {searcher_base:,} 文字")
    print(f"- 検索結果: {searcher_input:,} 文字")
    print(f"- 合計: {searcher_total:,} 文字")
    print(f"- 推定トークン数: {searcher_tokens:,} トークン\n")
    
    # 4. レポートノード（ReporterNode）
    print("### レポートノード (ReporterNode)")
    reporter_base = 1200  # プロンプトテンプレート推定
    reporter_input = 3000  # 評価履歴とサマリー
    reporter_total = reporter_base + reporter_input
    reporter_tokens = count_tokens_estimate(" " * reporter_total)
    
    print(f"- ベースプロンプト: {reporter_base:,} 文字")
    print(f"- 入力データ: {reporter_input:,} 文字")
    print(f"- 合計: {reporter_total:,} 文字")
    print(f"- 推定トークン数: {reporter_tokens:,} トークン\n")
    
    # 合計計算
    print("\n## 2. 1候補者あたりの使用量見積もり\n")
    
    # 各サイクルでの呼び出し
    cycle_calls = {
        "evaluator": 1,
        "gap_analyzer": 1,
        "searcher": 3,  # 平均3つのギャップを検索
    }
    
    # 3サイクル実行時の総使用量
    max_cycles = 3
    total_calls = 0
    total_tokens = 0
    
    print(f"### {max_cycles}サイクル実行時の詳細:")
    
    # RAG検索（初回のみ）
    rag_tokens = count_tokens_estimate(" " * 2000)
    print(f"\n初期処理:")
    print(f"- RAG検索: 1回 × {rag_tokens:,} トークン = {rag_tokens:,} トークン")
    total_calls += 1
    total_tokens += rag_tokens
    
    # 各サイクル
    for cycle in range(1, max_cycles + 1):
        print(f"\nサイクル {cycle}:")
        
        # 評価
        eval_calls = cycle_calls["evaluator"]
        eval_total = eval_calls * evaluator_tokens
        print(f"- 評価: {eval_calls}回 × {evaluator_tokens:,} トークン = {eval_total:,} トークン")
        total_calls += eval_calls
        total_tokens += eval_total
        
        # ギャップ分析
        gap_calls = cycle_calls["gap_analyzer"]
        gap_total = gap_calls * gap_analyzer_tokens
        print(f"- ギャップ分析: {gap_calls}回 × {gap_analyzer_tokens:,} トークン = {gap_total:,} トークン")
        total_calls += gap_calls
        total_tokens += gap_total
        
        # 検索
        search_calls = cycle_calls["searcher"]
        search_total = search_calls * searcher_tokens
        print(f"- 検索: {search_calls}回 × {searcher_tokens:,} トークン = {search_total:,} トークン")
        total_calls += search_calls
        total_tokens += search_total
    
    # 最終レポート
    print(f"\n最終処理:")
    print(f"- レポート生成: 1回 × {reporter_tokens:,} トークン = {reporter_tokens:,} トークン")
    total_calls += 1
    total_tokens += reporter_tokens
    
    print(f"\n### 1候補者あたりの合計:")
    print(f"- 総API呼び出し数: {total_calls}回")
    print(f"- 総トークン使用量: {total_tokens:,} トークン")
    print(f"- 平均トークン/呼び出し: {total_tokens // total_calls:,} トークン")
    
    # 100人処理時の推定
    print(f"\n## 3. 100人処理時の推定使用量\n")
    
    candidates_100_calls = total_calls * 100
    candidates_100_tokens = total_tokens * 100
    
    print(f"- 総API呼び出し数: {candidates_100_calls:,}回")
    print(f"- 総トークン使用量: {candidates_100_tokens:,} トークン ({candidates_100_tokens / 1_000_000:.1f}M トークン)")
    
    # Gemini API制限との比較
    print(f"\n## 4. Gemini API制限との比較\n")
    
    print("### Gemini 2.0 Flash (無料版)")
    print("- RPM (Requests Per Minute): 15")
    print("- TPM (Tokens Per Minute): 1,000,000")
    print("- RPD (Requests Per Day): 1,500")
    
    free_rpm_time = candidates_100_calls / 15
    free_tpm_time = candidates_100_tokens / 1_000_000
    free_rpd_days = candidates_100_calls / 1500
    
    print(f"\n100人処理に必要な時間（無料版）:")
    print(f"- RPM制限による時間: {free_rpm_time:.1f}分 ({free_rpm_time/60:.1f}時間)")
    print(f"- TPM制限による時間: {free_tpm_time:.1f}分")
    print(f"- RPD制限による日数: {free_rpd_days:.1f}日")
    print(f"→ ボトルネック: {'RPM制限' if free_rpm_time > free_tpm_time else 'TPM制限'}")
    
    print("\n### Gemini 2.0 Flash (有料版)")
    print("- RPM: 2,000 (推定)")
    print("- TPM: 4,000,000 (推定)")
    print("- コンテキストウィンドウ: 1,000,000 トークン")
    
    paid_rpm_time = candidates_100_calls / 2000
    paid_tpm_time = candidates_100_tokens / 4_000_000
    
    print(f"\n100人処理に必要な時間（有料版）:")
    print(f"- RPM制限による時間: {paid_rpm_time:.1f}分")
    print(f"- TPM制限による時間: {paid_tpm_time:.1f}分")
    print(f"→ ボトルネック: {'RPM制限' if paid_rpm_time > paid_tpm_time else 'TPM制限'}")
    
    print("\n### Gemini 2.5 Pro")
    print("- 料金: $1.25/1M入力トークン, $10/1M出力トークン")
    print("- コンテキストウィンドウ: 1,000,000+ トークン")
    
    # 入力/出力比を8:2と仮定
    input_tokens = candidates_100_tokens * 0.8
    output_tokens = candidates_100_tokens * 0.2
    
    input_cost = (input_tokens / 1_000_000) * 1.25
    output_cost = (output_tokens / 1_000_000) * 10
    total_cost = input_cost + output_cost
    
    print(f"\n100人処理のコスト（2.5 Pro）:")
    print(f"- 入力トークン: {input_tokens:,.0f} (${input_cost:.2f})")
    print(f"- 出力トークン: {output_tokens:,.0f} (${output_cost:.2f})")
    print(f"- 合計コスト: ${total_cost:.2f}")
    
    # 最適化提案
    print("\n## 5. 最適化提案\n")
    
    print("### トークン削減の方法:")
    print("1. **プロンプトの最適化**")
    print("   - 冗長な説明を削減")
    print("   - 構造化データの効率的な表現")
    print("   - 不要な履歴情報の削除")
    
    print("\n2. **キャッシュの活用**")
    print("   - 類似候補者の評価結果をキャッシュ")
    print("   - RAG検索結果の再利用")
    
    print("\n3. **並列処理の活用**")
    print("   - 複数候補者の同時処理")
    print("   - ノード間の並列実行")
    
    print("\n4. **動的なサイクル数調整**")
    print("   - 高スコア候補は早期終了")
    print("   - 低スコア候補も早期終了")
    print("   - 境界線の候補のみ深い分析")

if __name__ == "__main__":
    measure_prompt_sizes()