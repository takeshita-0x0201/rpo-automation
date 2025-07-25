"""
最終スコア統合と評価サマリー生成ノード
"""

from typing import Dict, List, Optional
import google.generativeai as genai

from .base import BaseNode, ResearchState, EvaluationResult, ScoreDetail
from ..utils.evaluation_formatters import EvaluationFormatters
from ..utils.semantic_guards import SemanticGuards
from ..prompts.scoring_criteria import ScoringCriteria, WeightProfile
from ..prompts.requirement_rules import RequirementRules


class FinalScorerNode(BaseNode):
    """各評価結果を統合して最終スコアとサマリーを生成するノード"""
    
    def __init__(self, api_key: str):
        super().__init__("FinalScorer")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash')
    
    async def process(self, state: ResearchState) -> ResearchState:
        """最終スコアの計算とサマリー生成"""
        self.state = "processing"
        
        print(f"  最終評価統合を開始（サイクル{state.current_cycle}）")
        
        # 部分スコアの集計
        partial_scores = getattr(state, 'partial_scores', {})
        
        # 最終スコアの計算
        final_score = self._calculate_final_score(partial_scores)
        
        # 構造化データの存在チェック
        has_structured_job_data = hasattr(state, 'structured_job_data') and state.structured_job_data
        has_structured_resume_data = hasattr(state, 'structured_resume_data') and state.structured_resume_data
        
        # セマンティックガードによる洞察
        guard_insights = self._apply_semantic_guards(state)
        
        # 評価履歴のフォーマット
        history_text = EvaluationFormatters.format_history(state.evaluation_history)
        
        # サマリー生成プロンプト
        prompt = f"""あなたは経験豊富な採用コンサルタントです。
各評価結果を統合して、最終的な評価サマリーを作成してください。

# 部分評価結果
{self._format_partial_scores(partial_scores)}

# 最終スコア
適合度スコア: {final_score}

# 追加の考慮事項
{guard_insights}

{history_text}

# 構造化データの有無
- 求人の構造化データ: {'あり' if has_structured_job_data else 'なし'}
- レジュメの構造化データ: {'あり' if has_structured_resume_data else 'なし'}

{RequirementRules.format_strengths_section()}

{RequirementRules.CONCERN_WRITING_RULES}

{ScoringCriteria.SUMMARY_FORMAT}

# 出力フォーマット
確信度: [低/中/高]

主な強み:
[必須要件との合致点を優先的に記載]

主な懸念点:
[必須要件の不足のみを記載]

評価サマリー:
[総合的な評価を記載]"""

        print(f"  LLMに最終評価サマリー生成プロンプト送信中...")
        response = self.model.generate_content(prompt)
        
        # 評価結果を構築
        evaluation = self._build_evaluation_result(
            response.text,
            final_score,
            partial_scores
        )
        
        # 状態を更新
        state.current_evaluation = evaluation
        self.state = "completed"
        
        return state
    
    def _calculate_final_score(self, partial_scores: Dict[str, ScoreDetail]) -> int:
        """部分スコアから最終スコアを計算"""
        total_score = 0
        
        # スキル評価（必須要件 + 歓迎要件）
        if 'skills' in partial_scores:
            skills = partial_scores['skills']
            if 'required_skills' in skills:
                total_score += skills['required_skills'].actual_score
            if 'preferred_skills' in skills:
                total_score += skills['preferred_skills'].actual_score
        
        # 実務経験
        if 'experience' in partial_scores:
            total_score += partial_scores['experience'].actual_score
        
        # 組織適合性
        if 'organizational_fit' in partial_scores:
            total_score += partial_scores['organizational_fit'].actual_score
        
        # 突出した経歴
        if 'outstanding_career' in partial_scores:
            total_score += partial_scores['outstanding_career'].actual_score
        
        return min(100, max(0, total_score))  # 0-100の範囲に制限
    
    def _format_partial_scores(self, partial_scores: Dict[str, any]) -> str:
        """部分スコアをフォーマット"""
        lines = []
        
        if 'skills' in partial_scores:
            skills = partial_scores['skills']
            if 'required_skills' in skills:
                detail = skills['required_skills']
                lines.append(f"## 必須要件: {detail.actual_score}/{detail.max_score}点")
                if detail.reasoning:
                    lines.append(detail.reasoning)
            
            if 'preferred_skills' in skills:
                detail = skills['preferred_skills']
                lines.append(f"\n## 歓迎要件: {detail.actual_score}/{detail.max_score}点")
                if detail.reasoning:
                    lines.append(detail.reasoning)
        
        if 'experience' in partial_scores:
            detail = partial_scores['experience']
            lines.append(f"\n## 実務遂行能力: {detail.actual_score}/{detail.max_score}点")
            if detail.reasoning:
                lines.append(detail.reasoning[:500] + "...")  # 長すぎる場合は省略
        
        if 'organizational_fit' in partial_scores:
            detail = partial_scores['organizational_fit']
            lines.append(f"\n## 組織適合性: {detail.actual_score}/{detail.max_score}点")
            if detail.reasoning:
                lines.append(detail.reasoning)
        
        if 'outstanding_career' in partial_scores:
            detail = partial_scores['outstanding_career']
            lines.append(f"\n## 突出した経歴: {detail.actual_score}/{detail.max_score}点")
            if detail.reasoning:
                lines.append(detail.reasoning)
        
        return '\n'.join(lines)
    
    def _apply_semantic_guards(self, state: ResearchState) -> str:
        """セマンティックガードレールを適用"""
        insights = []
        
        # 営業経験の検出
        if hasattr(state, 'job_description') and '営業' in state.job_description:
            has_sales, confidence, evidence = SemanticGuards.detect_sales_experience(state.resume)
            
            if evidence:
                insights.append("\n### セマンティック分析による営業経験の検出")
                insights.append(f"営業経験の可能性: {'高' if confidence > 0.7 else '中' if confidence > 0.4 else '低'} (確信度: {confidence:.1%})")
                insights.append("検出された要素:")
                for e in evidence[:3]:
                    insights.append(f"- {e}")
        
        return '\n'.join(insights) if insights else ""
    
    def _build_evaluation_result(
        self,
        response_text: str,
        final_score: int,
        partial_scores: Dict[str, ScoreDetail]
    ) -> EvaluationResult:
        """評価結果オブジェクトを構築"""
        import re
        
        # 確信度の抽出
        confidence_match = re.search(r'確信度:\s*([低中高])', response_text)
        confidence = confidence_match.group(1) if confidence_match else '中'
        
        # 強みと懸念点の抽出
        strengths = self._extract_list_section(response_text, "主な強み")
        concerns = self._extract_list_section(response_text, "主な懸念点")
        
        # サマリーの抽出
        summary = self._extract_summary(response_text)
        
        # スコア内訳の構築
        score_breakdown = {}
        
        if 'skills' in partial_scores:
            skills = partial_scores['skills']
            if 'required_skills' in skills:
                score_breakdown['必須要件'] = skills['required_skills']
            if 'preferred_skills' in skills:
                score_breakdown['歓迎要件'] = skills['preferred_skills']
        
        if 'experience' in partial_scores:
            score_breakdown['実務遂行能力'] = partial_scores['experience']
        
        if 'organizational_fit' in partial_scores:
            score_breakdown['組織適合性'] = partial_scores['organizational_fit']
        
        if 'outstanding_career' in partial_scores:
            score_breakdown['突出した経歴'] = partial_scores['outstanding_career']
        
        return EvaluationResult(
            score=final_score,
            confidence=confidence,
            strengths=strengths,
            concerns=concerns,
            summary=summary,
            score_breakdown=score_breakdown
        )
    
    def _extract_list_section(self, text: str, section_name: str) -> List[str]:
        """リスト形式のセクションを抽出"""
        import re
        
        pattern = rf"{section_name}:(.*?)(?=\n[^-\s]|\Z)"
        match = re.search(pattern, text, re.DOTALL)
        
        if match:
            content = match.group(1).strip()
            items = re.findall(r'[-•]\s*(.+)', content)
            return [item.strip() for item in items]
        
        return []
    
    def _extract_summary(self, text: str) -> str:
        """評価サマリーを抽出"""
        import re
        
        pattern = r'評価サマリー:(.*?)(?=\Z)'
        match = re.search(pattern, text, re.DOTALL)
        
        if match:
            return match.group(1).strip()
        
        return ""