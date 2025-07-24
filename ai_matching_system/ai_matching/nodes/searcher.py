"""
Tavily Web検索ノード
"""

import os
from typing import Dict, Any, List
from datetime import datetime
import google.generativeai as genai

from .base import BaseNode, ResearchState, SearchResult, InformationGap
from ..utils.reliability_scorer import ReliabilityScorer
from ..utils.parallel_executor import ParallelSearchExecutor


class TavilySearcherNode(BaseNode):
    """Tavily APIを使用してWeb検索を行うノード"""
    
    def __init__(self, api_key: str, tavily_api_key: str = None):
        super().__init__("TavilySearcher")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash')
        
        # Tavily APIキー（環境変数からも取得可能）
        self.tavily_api_key = tavily_api_key or os.getenv('TAVILY_API_KEY')
        
        # Tavily clientの初期化を試みる
        self.tavily_client = None
        try:
            from tavily import TavilyClient
            if self.tavily_api_key:
                self.tavily_client = TavilyClient(api_key=self.tavily_api_key)
        except ImportError:
            print("警告: Tavilyライブラリがインストールされていません。")
            print("pip install tavily-python でインストールしてください。")
    
    async def process(self, state: ResearchState) -> ResearchState:
        """情報ギャップに基づいて検索を実行"""
        self.state = "processing"
        
        # 検索対象がない場合
        if not state.information_gaps:
            print("  検索対象なし（情報ギャップが特定されていません）")
            self.state = "completed"
            return state
        
        print(f"  検索対象の情報ギャップ: {len(state.information_gaps)}件")
        
        # 重要度の高いものから最大2件まで検索
        gaps_to_search = sorted(
            state.information_gaps, 
            key=lambda x: {"高": 3, "中": 2, "低": 1}.get(x.importance, 0),
            reverse=True
        )[:2]
        
        print(f"  実際に検索する項目: {len(gaps_to_search)}件（重要度順）")
        
        # 並列検索実行器を使用
        parallel_executor = ParallelSearchExecutor(max_concurrent_searches=2)
        
        # 検索クエリを準備
        search_queries = {gap.info_type: gap for gap in gaps_to_search}
        
        print(f"\n  並列検索を開始...")
        search_results = await self._parallel_search_gaps(parallel_executor, search_queries)
        
        # 結果を状態に追加
        for gap_type, search_result in search_results.items():
            if search_result:
                state.add_search_result(gap_type, search_result)
                print(f"    {gap_type}: 成功（{len(search_result.results)}件の結果）")
            else:
                print(f"    {gap_type}: 検索結果なし")
        
        self.state = "completed"
        return state
    
    async def _parallel_search_gaps(self, executor: ParallelSearchExecutor, 
                                   gaps: Dict[str, InformationGap]) -> Dict[str, SearchResult]:
        """複数の情報ギャップを並列検索"""
        # タスクリストを作成
        tasks = [
            (gap_type, self._search_information, {"gap": gap})
            for gap_type, gap in gaps.items()
        ]
        
        # 並列実行
        report = await executor.executor.execute_parallel_async(tasks, timeout=30)
        
        # 結果をマッピング
        results = {}
        for task_result in report.task_results:
            if task_result.success and task_result.result:
                results[task_result.task_id] = task_result.result
        
        # 実行レポートを出力
        print(f"\n  並列検索完了:")
        print(f"    成功: {report.successful_tasks}/{report.total_tasks}")
        print(f"    実行時間: {report.total_duration:.1f}秒")
        print(f"    並列効率: {report.parallel_efficiency:.1f}x")
        
        return results
    
    async def _search_information(self, gap: InformationGap) -> SearchResult:
        """個別の情報を検索"""
        
        if self.tavily_client:
            # 実際のTavily検索
            try:
                print(f"    Tavily APIで検索中...")
                search_response = self.tavily_client.search(
                    query=gap.search_query,
                    search_depth="advanced",
                    max_results=5
                )
                print(f"    Tavily検索完了")
                
                # 結果を整形し、信頼性を評価
                results = []
                sources = []
                
                for result in search_response.get('results', []):
                    # 信頼性スコアを計算
                    reliability_info = ReliabilityScorer.score_source(
                        result.get('url', ''),
                        result.get('content', ''),
                        result.get('published_date')
                    )
                    
                    results.append({
                        'title': result.get('title', ''),
                        'content': result.get('content', ''),
                        'url': result.get('url', ''),
                        'score': result.get('score', 0),
                        'reliability': reliability_info['reliability_score'],
                        'reliability_warnings': reliability_info['warnings']
                    })
                    sources.append(result.get('url', ''))
                
                # 信頼性の高い順にソート
                results.sort(key=lambda x: x.get('reliability', 0), reverse=True)
                
                # 結果を要約
                summary = await self._summarize_search_results(results, gap)
                
                return SearchResult(
                    query=gap.search_query,
                    results=results,
                    summary=summary,
                    sources=sources[:3],  # 上位3つのソース
                    timestamp=datetime.now().isoformat()
                )
                
            except Exception as e:
                print(f"Tavily検索エラー: {e}")
                # フォールバックとしてシミュレーション検索を実行
                return await self._simulate_search(gap)
        else:
            # Tavilyが利用できない場合はシミュレーション
            return await self._simulate_search(gap)
    
    async def _summarize_search_results(self, results: list, gap: InformationGap) -> str:
        """検索結果を要約（信頼性を考慮）"""
        if not results:
            return "関連する情報が見つかりませんでした。"
        
        # 信頼性の高い上位3件の内容を結合
        contents = []
        reliable_results = [r for r in results if r.get('reliability', 0) >= 0.6]
        
        if not reliable_results:
            # 信頼できる結果がない場合は警告付きで使用
            print("    警告: 信頼性の高い情報源が見つかりませんでした")
            reliable_results = results[:3]
        
        for result in reliable_results[:3]:
            if result.get('content'):
                reliability = result.get('reliability', 0)
                warnings = result.get('reliability_warnings', [])
                warning_str = f" (注意: {', '.join(warnings)})" if warnings else ""
                contents.append(f"- [信頼度: {reliability:.1f}]{warning_str} {result['content'][:200]}...")
        
        # 矛盾がないか確認
        if len(reliable_results) > 1:
            contradiction_info = ReliabilityScorer.resolve_contradictions(reliable_results)
            if contradiction_info['contradictions']:
                print(f"    警告: {len(contradiction_info['contradictions'])}件の矛盾が検出されました")
        
        # 企業規模比較の場合は特別な処理
        if gap.info_type == "企業規模比較":
            prompt = f"""検索結果から企業規模情報を抽出し、規模差の影響を分析します。

# 情報ニーズ
- 種類: {gap.info_type}
- 質問: {gap.description}
- 影響: {gap.rationale}

# 検索結果
{chr(10).join(contents[:3])}

# 企業規模の分類基準
- 大企業: 従業員1000人以上
- 中堅企業: 従業員300-999人
- 中小企業: 従業員50-299人
- 小規模企業: 従業員50人未満

# 要約指示（200-250文字）
1. 検出された企業規模（従業員数を明記）
2. 規模差による影響評価（文化、働き方、意思決定速度など）
3. 適応に関する推奨事項

※規模差が2段階以上（例：大企業→中小企業）の場合は要注意として明記。"""
        else:
            # 通常の検索結果要約
            prompt = f"""検索結果から採用判断に必要な情報を抽出します。

# 情報ニーズ
- 種類: {gap.info_type}
- 質問: {gap.description}
- 影響: {gap.rationale}

# 検索結果
{chr(10).join(contents[:3])}

# 要約指示（200-250文字）
1. 主要な発見（1-2文）
2. 採用評価への示唆（1-2文）
3. 追加確認事項（1文・任意）

専門用語は最小限にし、採用担当者向けに簡潔に記述。"""
        
        response = self.model.generate_content(prompt)
        return response.text.strip()
    
    async def _simulate_search(self, gap: InformationGap) -> SearchResult:
        """Tavilyが利用できない場合のシミュレーション検索"""
        print(f"    シミュレーション検索を実行中...")
        # 最適化されたシミュレーションプロンプト
        prompt = f"""採用評価専門家として情報を提供します。

# 情報ニーズ
- クエリ: {gap.search_query}
- タイプ: {gap.info_type}
- 質問: {gap.description}

# 回答指示（200-250文字）
1. 業界標準（1-2文）
2. 実務的アドバイス（1-2文）
3. 確認ポイント（1文）

客観的・信頼性の高い情報として記述。"""
        
        response = self.model.generate_content(prompt)
        summary = response.text.strip()
        
        return SearchResult(
            query=gap.search_query,
            results=[{
                'title': f'シミュレーション: {gap.info_type}',
                'content': summary,
                'url': 'simulated',
                'score': 1.0
            }],
            summary=summary,
            sources=['シミュレーション検索'],
            timestamp=datetime.now().isoformat()
        )