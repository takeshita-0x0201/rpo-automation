"""
ノードオーケストレーター
各ノードを管理し、処理フローを制御する
"""

import asyncio
import time
from typing import Dict, List, Optional
from datetime import datetime
import json

from .base import ResearchState, CycleResult
from .evaluator import EvaluatorNode
from .gap_analyzer import GapAnalyzerNode
from .searcher import TavilySearcherNode
from .reporter import ReportGeneratorNode


class DeepResearchOrchestrator:
    """DeepResearchの処理フローを管理するオーケストレーター"""
    
    def __init__(self, gemini_api_key: str, tavily_api_key: Optional[str] = None):
        """
        Args:
            gemini_api_key: Gemini APIキー
            tavily_api_key: Tavily APIキー（オプション）
        """
        # 各ノードを初期化
        self.evaluator = EvaluatorNode(gemini_api_key)
        self.gap_analyzer = GapAnalyzerNode(gemini_api_key)
        self.searcher = TavilySearcherNode(gemini_api_key, tavily_api_key)
        self.reporter = ReportGeneratorNode(gemini_api_key)
        
        # ノードのリスト（処理順）
        self.cycle_nodes = [self.evaluator, self.gap_analyzer, self.searcher]
        self.final_node = self.reporter
    
    async def run(
        self,
        resume: str,
        job_description: str,
        job_memo: str,
        max_cycles: int = 3
    ) -> Dict:
        """
        DeepResearchプロセスを実行
        
        Args:
            resume: 候補者のレジュメ
            job_description: 求人票
            job_memo: 求人メモ
            max_cycles: 最大サイクル数
            
        Returns:
            処理結果の辞書
        """
        # 初期状態を作成
        state = ResearchState(
            resume=resume,
            job_memo=job_memo,
            job_description=job_description if job_description else None,
            max_cycles=max_cycles
        )
        
        print("=== DeepResearch 分離型マッチング開始 ===")
        print(f"最大サイクル数: {max_cycles}")
        print("\n【入力データ】")
        print(f"レジュメ文字数: {len(resume)}文字")
        print(f"求人メモ文字数: {len(job_memo)}文字")
        if job_description:
            print(f"求人票文字数: {len(job_description)}文字")
        print("-" * 70)
        
        # 評価サイクルを実行
        while state.should_continue and state.current_cycle < state.max_cycles:
            cycle_start = time.time()
            print(f"\n--- サイクル {state.current_cycle + 1} ---")
            
            # サイクル内の各ノードを順次実行
            for node in self.cycle_nodes:
                # ノード実行（表示なし）
                node_start = time.time()
                state = await node.process(state)
                node_duration = time.time() - node_start
                print(f"  処理時間: {node_duration:.2f}秒")
                
                # 各ノードの結果を詳細表示
                if node.name == "Evaluator" and state.current_evaluation:
                    print(f"  評価スコア: {state.current_evaluation.score}/100")
                    print(f"  確信度: {state.current_evaluation.confidence}")
                    print(f"  強み:")
                    for strength in state.current_evaluation.strengths[:2]:
                        print(f"    - {strength}")
                    print(f"  懸念:")
                    for concern in state.current_evaluation.concerns[:2]:
                        print(f"    - {concern}")
                    print(f"  サマリー: {state.current_evaluation.summary[:100]}...")
                    
                elif node.name == "GapAnalyzer":
                    print(f"  情報ギャップ: {len(state.information_gaps)}件")
                    if state.information_gaps:
                        for i, gap in enumerate(state.information_gaps[:3], 1):
                            print(f"    {i}. {gap.info_type} (重要度: {gap.importance})")
                            print(f"       検索クエリ: {gap.search_query}")
                    else:
                        print("  → 追加情報不要（十分な確信度）")
                        
                elif node.name == "TavilySearcher":
                    new_searches = len(state.search_results) - sum(len(c.search_results) for c in state.evaluation_history)
                    print(f"  新規検索実行: {new_searches}件")
                    print(f"  累計検索結果: {len(state.search_results)}件")
                    for key in list(state.search_results.keys())[-new_searches:]:
                        result = state.search_results[key]
                        print(f"    - {key}: {result.summary[:80]}...")
            
            # サイクル結果を記録
            cycle_duration = time.time() - cycle_start
            cycle_result = CycleResult(
                cycle_number=state.current_cycle + 1,
                evaluation=state.current_evaluation,
                gaps=state.information_gaps.copy(),
                search_results=state.search_results.copy(),
                duration_seconds=cycle_duration
            )
            state.complete_cycle(cycle_result)
            
            # サイクル完了情報
            print(f"\nサイクル{state.current_cycle}完了:")
            print(f"  処理時間: {cycle_duration:.2f}秒")
            print(f"  評価履歴数: {len(state.evaluation_history)}件")
            
            # 継続判定（gap_analyzerが設定）
            if not state.should_continue:
                print("\n→ 十分な確信度に到達、または追加情報不要と判断されました")
                break
            elif state.current_cycle >= state.max_cycles:
                print("\n→ 最大サイクル数に到達しました")
        
        # 最終レポート生成
        print("\n--- 最終レポート生成 ---")
        report_start = time.time()
        state = await self.final_node.process(state)
        report_duration = time.time() - report_start
        print(f"レポート生成時間: {report_duration:.2f}秒")
        
        # 結果を整形して返す
        return self._format_final_result(state)
    
    def _format_final_result(self, state: ResearchState) -> Dict:
        """最終結果を整形"""
        return {
            'final_judgment': state.final_judgment,
            'evaluation_history': [
                {
                    'cycle': cycle.cycle_number,
                    'score': cycle.evaluation.score,
                    'confidence': cycle.evaluation.confidence,
                    'gaps_found': len(cycle.gaps),
                    'searches_performed': len(cycle.search_results),
                    'duration': round(cycle.duration_seconds, 2)
                }
                for cycle in state.evaluation_history
            ],
            'total_cycles': len(state.evaluation_history),
            'total_searches': sum(len(cycle.search_results) for cycle in state.evaluation_history),
            'final_score': state.current_evaluation.score if state.current_evaluation else None,
            'final_confidence': state.current_evaluation.confidence if state.current_evaluation else None
        }


# 同期的なインターフェース
class SeparatedDeepResearchMatcher:
    """同期的に使用できるラッパークラス"""
    
    def __init__(self, gemini_api_key: str, tavily_api_key: Optional[str] = None):
        self.orchestrator = DeepResearchOrchestrator(gemini_api_key, tavily_api_key)
    
    def match_candidate(
        self,
        resume_file: str,
        job_description_file: str,
        job_memo_file: str,
        max_cycles: int = 3
    ) -> Dict:
        """
        ファイルから読み込んでマッチングを実行
        
        Args:
            resume_file: レジュメファイルのパス
            job_description_file: 求人票ファイルのパス
            job_memo_file: 求人メモファイルのパス
            max_cycles: 最大サイクル数
            
        Returns:
            マッチング結果
        """
        # ファイルを読み込む
        print(f"\nファイル読み込み中...")
        with open(resume_file, 'r', encoding='utf-8') as f:
            resume = f.read()
            print(f"  レジュメ読み込み完了: {len(resume)}文字")
        
        # job_description_fileがNoneまたは空の場合はスキップ
        if job_description_file and job_description_file != "":
            try:
                with open(job_description_file, 'r', encoding='utf-8') as f:
                    job_description = f.read()
                    print(f"  求人票読み込み完了: {len(job_description)}文字")
            except:
                job_description = None
                print(f"  求人票なし（求人メモのみで評価）")
        else:
            job_description = None
            print(f"  求人票なし（求人メモのみで評価）")
            
        with open(job_memo_file, 'r', encoding='utf-8') as f:
            job_memo = f.read()
            print(f"  求人メモ読み込み完了: {len(job_memo)}文字")
        
        # 非同期処理を同期的に実行
        return asyncio.run(
            self.orchestrator.run(
                resume=resume,
                job_description=job_description,
                job_memo=job_memo,
                max_cycles=max_cycles
            )
        )