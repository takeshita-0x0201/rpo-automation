"""
モジュール化されたDeepResearchマッチングシステム
各処理を分離しつつ、統合的な使用も可能
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from dataclasses import dataclass
import google.generativeai as genai


# ========== データ構造 ==========
@dataclass
class MatchingContext:
    """マッチングのコンテキスト"""
    resume: str
    job_description: str
    job_memo: str
    additional_info: Dict = None
    history: List = None
    
    def __post_init__(self):
        if self.additional_info is None:
            self.additional_info = {}
        if self.history is None:
            self.history = []


@dataclass
class EvaluationResult:
    score: int
    confidence: str
    strengths: List[str]
    concerns: List[str]
    summary: str


@dataclass
class InformationGap:
    info_type: str
    query: str
    importance: str


# ========== 基底クラス ==========
class BaseProcessor(ABC):
    """処理ノードの基底クラス"""
    
    def __init__(self, llm_model):
        self.llm = llm_model
    
    @abstractmethod
    def process(self, context: MatchingContext) -> Dict:
        pass


# ========== 個別処理ノード ==========
class CandidateEvaluator(BaseProcessor):
    """候補者評価ノード"""
    
    def process(self, context: MatchingContext) -> EvaluationResult:
        """現在の情報で候補者を評価"""
        
        # 追加情報のフォーマット
        additional_info_text = self._format_additional_info(context.additional_info)
        
        prompt = f"""
以下の情報を基に候補者を評価してください。

【候補者レジュメ】
{context.resume}

【求人票】
{context.job_description}

【求人メモ】
{context.job_memo}
{additional_info_text}

評価を以下の形式で：
適合度スコア: [0-100]
確信度: [低/中/高]
主な強み:
- [箇条書き3つまで]
主な懸念点:
- [箇条書き3つまで]
評価サマリー: [1-2文]
"""
        
        response = self.llm.generate_content(prompt)
        return self._parse_evaluation(response.text)
    
    def _format_additional_info(self, info: Dict) -> str:
        if not info:
            return ""
        
        text = "\n【追加収集情報】\n"
        for key, value in info.items():
            text += f"\n■ {key}\n{value['summary']}\n"
        return text
    
    def _parse_evaluation(self, text: str) -> EvaluationResult:
        # パース処理（簡略化）
        return EvaluationResult(
            score=75,
            confidence="中",
            strengths=["経験豊富", "システム知識"],
            concerns=["英語力"],
            summary="基本要件は満たしている"
        )


class GapAnalyzer(BaseProcessor):
    """情報ギャップ分析ノード"""
    
    def process(self, context: MatchingContext, evaluation: EvaluationResult) -> List[InformationGap]:
        """評価結果から不足情報を特定"""
        
        collected = list(context.additional_info.keys())
        
        prompt = f"""
現在の評価：
- スコア: {evaluation.score}
- 確信度: {evaluation.confidence}
- 懸念点: {', '.join(evaluation.concerns)}

既に収集済み: {collected}

判断の確実性を高めるために必要な追加情報を最大3つ特定してください。

形式：
情報1:
種類: [何を知りたいか]
検索クエリ: [検索用クエリ]
重要度: [高/中/低]

確信度が「高」の場合は「追加情報不要」と回答。
"""
        
        response = self.llm.generate_content(prompt)
        return self._parse_gaps(response.text)
    
    def _parse_gaps(self, text: str) -> List[InformationGap]:
        if "追加情報不要" in text:
            return []
        # パース処理（簡略化）
        return [
            InformationGap(
                info_type="英語使用経験",
                query="財務 英語 実務レベル",
                importance="高"
            )
        ]


class InformationSearcher(BaseProcessor):
    """情報検索ノード"""
    
    def __init__(self, llm_model, search_api=None):
        super().__init__(llm_model)
        self.search_api = search_api  # 実際のWeb検索API
    
    def process(self, gaps: List[InformationGap]) -> Dict[str, Dict]:
        """不足情報を検索"""
        
        results = {}
        for gap in gaps[:2]:  # 最大2件
            if self.search_api:
                # 実際のWeb検索
                search_results = self.search_api.search(gap.query)
                summary = self._summarize_results(search_results, gap.info_type)
            else:
                # シミュレーション
                summary = self._simulate_search(gap)
            
            results[gap.info_type] = {
                'query': gap.query,
                'summary': summary,
                'sources': ['simulated']
            }
        
        return results
    
    def _simulate_search(self, gap: InformationGap) -> str:
        prompt = f"""
検索クエリ「{gap.query}」の検索結果を要約してください。
{gap.info_type}に関する有用な情報を200文字程度で。
"""
        response = self.llm.generate_content(prompt)
        return response.text


class ReportGenerator(BaseProcessor):
    """最終レポート生成ノード"""
    
    def process(self, context: MatchingContext, history: List) -> Dict:
        """最終判定レポートを生成"""
        
        journey = self._format_journey(history)
        
        prompt = f"""
{len(history)}回の評価サイクルの結果：

{journey}

最終判定：
推奨度: [A/B/C/D]
判定理由:
- 強み（3つ）
- 懸念点（2つ）
- 総合評価

面接確認事項:（3つ）
"""
        
        response = self.llm.generate_content(prompt)
        return self._parse_final_judgment(response.text)
    
    def _format_journey(self, history: List) -> str:
        text = ""
        for i, cycle in enumerate(history, 1):
            text += f"\nサイクル{i}: "
            text += f"スコア{cycle['evaluation'].score} "
            text += f"({cycle['evaluation'].confidence})\n"
        return text
    
    def _parse_final_judgment(self, text: str) -> Dict:
        # パース処理（簡略化）
        return {
            'recommendation': 'B',
            'strengths': ['財務経験', 'システム知識', 'マネジメント'],
            'concerns': ['英語力', 'グローバル経験'],
            'overall_assessment': '基本要件は満たす',
            'interview_points': ['英語使用経験', '適応力', '意欲']
        }


# ========== オーケストレーター ==========
class ModularDeepResearchMatcher:
    """モジュール化されたマッチャー"""
    
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        llm = genai.GenerativeModel('gemini-2.0-flash')
        
        # 各処理ノードを初期化
        self.evaluator = CandidateEvaluator(llm)
        self.gap_analyzer = GapAnalyzer(llm)
        self.searcher = InformationSearcher(llm)
        self.reporter = ReportGenerator(llm)
    
    def match_candidate(
        self,
        resume_file: str,
        job_desc_file: str,
        job_memo_file: str,
        max_cycles: int = 3
    ) -> Dict:
        """候補者マッチング実行"""
        
        # コンテキスト作成
        context = MatchingContext(
            resume=self._load_file(resume_file),
            job_description=self._load_file(job_desc_file),
            job_memo=self._load_file(job_memo_file)
        )
        
        history = []
        
        # 評価サイクル
        for cycle in range(max_cycles):
            print(f"\n=== サイクル {cycle + 1} ===")
            
            # 1. 評価
            evaluation = self.evaluator.process(context)
            print(f"評価: {evaluation.score} ({evaluation.confidence})")
            
            # 2. ギャップ分析
            gaps = self.gap_analyzer.process(context, evaluation)
            print(f"不足情報: {len(gaps)}件")
            
            if not gaps:
                history.append({
                    'cycle': cycle + 1,
                    'evaluation': evaluation,
                    'gaps': [],
                    'search_results': {}
                })
                break
            
            # 3. 情報検索
            search_results = self.searcher.process(gaps)
            context.additional_info.update(search_results)
            
            history.append({
                'cycle': cycle + 1,
                'evaluation': evaluation,
                'gaps': gaps,
                'search_results': search_results
            })
        
        # 4. 最終レポート生成
        final_report = self.reporter.process(context, history)
        
        return {
            'final_judgment': final_report,
            'history': history,
            'total_cycles': len(history)
        }
    
    def _load_file(self, filepath: str) -> str:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()


# ========== 使用例 ==========
if __name__ == "__main__":
    import os
    
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("GEMINI_API_KEY環境変数を設定してください")
        exit(1)
    
    # モジュール化されたマッチャーを使用
    matcher = ModularDeepResearchMatcher(api_key)
    
    result = matcher.match_candidate(
        'sample_data/resume.txt',
        'sample_data/job_description.txt',
        'sample_data/job_memo.txt'
    )
    
    print(f"\n推奨度: {result['final_judgment']['recommendation']}")