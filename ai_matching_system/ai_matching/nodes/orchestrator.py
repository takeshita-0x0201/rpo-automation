"""
ノードオーケストレーター
各ノードを管理し、処理フローを制御する
"""

import asyncio
import time
from typing import Dict, List, Optional
from datetime import datetime
import json
import os

from .base import ResearchState, CycleResult
from .evaluator import EvaluatorNode
from .evaluator_enhanced import EnhancedEvaluatorNode
from .hybrid_evaluator import HybridEvaluatorNode
from .gap_analyzer import GapAnalyzerNode
from .searcher import TavilySearcherNode
from .reporter import ReportGeneratorNode
from .rag_searcher import RAGSearcherNode
from .adaptive_search_strategy import AdaptiveSearchStrategyNode
from ..utils.parallel_executor import ParallelExecutor


class DeepResearchOrchestrator:
    """DeepResearchの処理フローを管理するオーケストレーター"""
    
    def __init__(self, gemini_api_key: str, tavily_api_key: Optional[str] = None, 
                 pinecone_api_key: Optional[str] = None, use_enhanced_evaluator: bool = True,
                 use_hybrid_evaluator: bool = False):
        """
        Args:
            gemini_api_key: Gemini APIキー
            tavily_api_key: Tavily APIキー（オプション）
            pinecone_api_key: Pinecone APIキー（オプション）
            use_enhanced_evaluator: 強化版評価ノードを使用するか（デフォルト: True）
            use_hybrid_evaluator: ハイブリッド評価ノードを使用するか（デフォルト: False）
        """
        # 各ノードを初期化
        self.rag_searcher = RAGSearcherNode(gemini_api_key, pinecone_api_key)
        
        # 評価ノードの選択（環境変数も考慮）
        use_hybrid = use_hybrid_evaluator or os.getenv("USE_HYBRID_EVALUATOR", "false").lower() == "true"
        
        if use_hybrid:
            self.evaluator = HybridEvaluatorNode(gemini_api_key, os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY"))
            print("[Orchestrator] ハイブリッド評価ノードを使用します")
        elif use_enhanced_evaluator:
            self.evaluator = EnhancedEvaluatorNode(gemini_api_key, os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY"))
            print("[Orchestrator] 強化版評価ノードを使用します")
        else:
            self.evaluator = EvaluatorNode(gemini_api_key, os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY"))
            print("[Orchestrator] 標準評価ノードを使用します")
        
        self.gap_analyzer = GapAnalyzerNode(gemini_api_key)
        self.adaptive_strategy = AdaptiveSearchStrategyNode()
        self.searcher = TavilySearcherNode(gemini_api_key, tavily_api_key)
        self.reporter = ReportGeneratorNode(gemini_api_key)
        
        # ノードのリスト（処理順）
        # RAG検索は最初に実行
        self.initial_nodes = [self.rag_searcher]
        # 動的戦略ノードをgap_analyzerの後に追加
        self.cycle_nodes = [self.evaluator, self.gap_analyzer, self.adaptive_strategy, self.searcher]
        self.final_node = self.reporter
    
    async def run(
        self,
        resume: str,
        job_description: str,
        job_memo: str,
        max_cycles: int = 3,
        candidate_id: Optional[str] = None,
        candidate_age: Optional[int] = None,
        candidate_gender: Optional[str] = None,
        candidate_company: Optional[str] = None,
        enrolled_company_count: Optional[int] = None,
        structured_job_data: Optional[Dict] = None
    ) -> Dict:
        """
        DeepResearchプロセスを実行
        
        Args:
            resume: 候補者のレジュメ
            job_description: 求人票
            job_memo: 求人メモ
            max_cycles: 最大サイクル数
            candidate_id: 候補者ID
            candidate_age: 候補者の年齢
            candidate_gender: 候補者の性別
            candidate_company: 現在の所属企業
            enrolled_company_count: 在籍企業数
            structured_job_data: 構造化された求人データ（給与、スキル要件等）
            
        Returns:
            処理結果の辞書
        """
        # 初期状態を作成
        state = ResearchState(
            resume=resume,
            job_memo=job_memo,
            job_description=job_description if job_description else None,
            max_cycles=max_cycles,
            candidate_id=candidate_id,
            candidate_age=candidate_age,
            candidate_gender=candidate_gender,
            candidate_company=candidate_company,
            enrolled_company_count=enrolled_company_count,
            structured_job_data=structured_job_data
        )
        
        print("=== DeepResearch 分離型マッチング開始 ===")
        print(f"最大サイクル数: {max_cycles}")
        print("\n【入力データ】")
        print(f"レジュメ文字数: {len(resume)}文字")
        if job_description:
            print(f"求人情報文字数: {len(job_description)}文字")
        print(f"求人補足情報文字数: {len(job_memo)}文字")
        
        # 候補者情報を取得して表示
        await self._display_candidate_info(state)
        
        print("-" * 70)
        
        # 初期処理（RAG検索）を実行
        print("\n--- 初期処理: 類似ケース検索 ---")
        for node in self.initial_nodes:
            node_start = time.time()
            state = await node.process(state)
            node_duration = time.time() - node_start
            print(f"  処理時間: {node_duration:.2f}秒")
            
            # RAG検索結果を表示
            if hasattr(state, 'rag_insights') and state.rag_insights:
                insights = state.rag_insights
                print(f"  類似ケース数: {insights.get('total_cases', 0)}")
                if insights.get('client_tendency'):
                    print(f"  最頻出評価: {insights['client_tendency']['most_common_evaluation']} ({insights['client_tendency']['percentage']:.1f}%)")
                if insights.get('risk_factors'):
                    print(f"  リスク要因: {len(insights['risk_factors'])}件検出")
        
        # 評価サイクルを実行
        while state.should_continue and state.current_cycle < state.max_cycles:
            cycle_start = time.time()
            print(f"\n--- サイクル {state.current_cycle + 1} ---")
            
            # 並列実行可能なノードをグループ化
            # 評価は必須、その後のgap_analyzerとadaptive_strategyを並列実行
            evaluator_start = time.time()
            state = await self.evaluator.process(state)
            evaluator_duration = time.time() - evaluator_start
            print(f"  評価ノード処理時間: {evaluator_duration:.2f}秒")
            
            # 評価結果を表示
            if state.current_evaluation:
                print(f"  評価スコア: {state.current_evaluation.score}/100")
                print(f"  確信度: {state.current_evaluation.confidence}")
                print(f"  強み:")
                for strength in state.current_evaluation.strengths[:2]:
                    print(f"    - {strength}")
                print(f"  懸念:")
                for concern in state.current_evaluation.concerns[:2]:
                    print(f"    - {concern}")
            
            # gap_analyzerとadaptive_strategyを並列実行
            parallel_executor = ParallelExecutor(max_workers=2)
            parallel_tasks = [
                ("GapAnalyzer", self.gap_analyzer.process, {"state": state}),
                ("AdaptiveStrategy", self.adaptive_strategy.process, {"state": state})
            ]
            
            print(f"\n  ギャップ分析と適応戦略を並列実行...")
            parallel_start = time.time()
            report = await parallel_executor.execute_parallel_async(parallel_tasks)
            parallel_duration = time.time() - parallel_start
            
            # 並列実行結果を反映
            for task_result in report.task_results:
                if task_result.success and task_result.result:
                    state = task_result.result
            
            print(f"  並列処理完了: {parallel_duration:.2f}秒 (効率: {report.parallel_efficiency:.1f}x)")
            
            # ギャップ分析結果を表示
            print(f"  情報ギャップ: {len(state.information_gaps)}件")
            if state.information_gaps:
                for i, gap in enumerate(state.information_gaps[:3], 1):
                    print(f"    {i}. {gap.info_type} (重要度: {gap.importance})")
            
            # 検索を実行
            if state.information_gaps:
                searcher_start = time.time()
                state = await self.searcher.process(state)
                searcher_duration = time.time() - searcher_start
                print(f"  検索ノード処理時間: {searcher_duration:.2f}秒")
                
                new_searches = len(state.search_results) - sum(len(c.search_results) for c in state.evaluation_history)
                print(f"  新規検索実行: {new_searches}件")
                print(f"  累計検索結果: {len(state.search_results)}件")
                
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
    
    async def _display_candidate_info(self, state: ResearchState) -> None:
        """候補者情報を表示"""
        print("\n【候補者情報】")
        
        # stateに直接設定された候補者情報を使用
        info_parts = []
        
        if hasattr(state, 'candidate_age') and state.candidate_age is not None:
            info_parts.append(f"年齢: {state.candidate_age}歳")
        
        if hasattr(state, 'candidate_gender') and state.candidate_gender:
            info_parts.append(f"性別: {state.candidate_gender}")
            
        if hasattr(state, 'candidate_company') and state.candidate_company:
            info_parts.append(f"現在の所属: {state.candidate_company}")
            
        if hasattr(state, 'enrolled_company_count') and state.enrolled_company_count is not None:
            info_parts.append(f"在籍企業数: {state.enrolled_company_count}社")
        
        if info_parts:
            for info in info_parts:
                print(info)
        else:
            print("候補者基本情報が提供されていません")
    
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
            'final_confidence': state.current_evaluation.confidence if state.current_evaluation else None,
            'model_version': 'gemini-2.0-flash'  # モデルバージョンを追加
        }


# 同期的なインターフェース
class SeparatedDeepResearchMatcher:
    """同期的に使用できるラッパークラス"""
    
    def __init__(self, gemini_api_key: str, tavily_api_key: Optional[str] = None,
                 pinecone_api_key: Optional[str] = None):
        self.orchestrator = DeepResearchOrchestrator(gemini_api_key, tavily_api_key, pinecone_api_key)
    
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
        
        # レジュメから候補者IDを抽出
        candidate_id = self._extract_candidate_id_from_resume(resume)
        if candidate_id:
            print(f"  レジュメから候補者ID '{candidate_id}' を抽出しました")
        
        # 非同期処理を同期的に実行
        return asyncio.run(
            self.orchestrator.run(
                resume=resume,
                job_description=job_description,
                job_memo=job_memo,
                max_cycles=max_cycles,
                candidate_id=candidate_id
            )
        )
        
    def _extract_candidate_id_from_resume(self, resume_text: str) -> Optional[str]:
        """レジュメから候補者IDを抽出"""
        if not resume_text:
            return None
            
        lines = resume_text.strip().split('\n')
        for line in lines[:10]:  # 最初の10行をチェック
            if 'ID:' in line or 'candidate_id:' in line.lower() or 'candidate id:' in line.lower():
                return line.split(':', 1)[-1].strip()
                
        return None
    
    def match_candidate_direct(
        self,
        resume_text: str,
        job_description_text: str,
        job_memo_text: str,
        max_cycles: int = 3,
        candidate_id: Optional[str] = None,
        candidate_age: Optional[int] = None,
        candidate_gender: Optional[str] = None,
        candidate_company: Optional[str] = None,
        enrolled_company_count: Optional[int] = None,
        structured_job_data: Optional[Dict] = None
    ) -> Dict:
        """
        テキストを直接渡してマッチングを実行
        
        Args:
            resume_text: レジュメテキスト
            job_description_text: 求人票テキスト
            job_memo_text: 求人メモテキスト
            max_cycles: 最大サイクル数
            candidate_id: 候補者ID（オプション）
            candidate_age: 候補者の年齢
            candidate_gender: 候補者の性別
            candidate_company: 現在の所属企業
            enrolled_company_count: 在籍企業数
            structured_job_data: 構造化された求人データ
            
        Returns:
            マッチング結果
        """
        print(f"\nデータ受信...")
        print(f"  レジュメ: {len(resume_text)}文字")
        if job_description_text:
            print(f"  求人情報: {len(job_description_text)}文字")
            # デバッグ: 求人情報の冒頭を表示
            if len(job_description_text) < 100:
                print(f"  [警告] 求人情報が短すぎます: '{job_description_text}'")
        else:
            print(f"  求人情報なし")
        print(f"  求人補足情報: {len(job_memo_text)}文字")
        
        # 構造化データの確認
        if structured_job_data:
            print(f"  構造化データ: {list(structured_job_data.keys())}")
        else:
            print(f"  構造化データなし")
        
        # 候補者IDが指定されていない場合はレジュメから抽出
        if not candidate_id:
            candidate_id = self._extract_candidate_id_from_resume(resume_text)
            if candidate_id:
                print(f"  レジュメから候補者ID '{candidate_id}' を抽出しました")
        else:
            print(f"  候補者ID: {candidate_id}")
        
        # 非同期処理を同期的に実行
        return asyncio.run(
            self.orchestrator.run(
                resume=resume_text,
                job_description=job_description_text,
                job_memo=job_memo_text,
                max_cycles=max_cycles,
                candidate_id=candidate_id,
                candidate_age=candidate_age,
                candidate_gender=candidate_gender,
                candidate_company=candidate_company,
                enrolled_company_count=enrolled_company_count,
                structured_job_data=structured_job_data
            )
        )