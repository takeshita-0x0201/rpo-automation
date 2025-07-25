"""
スキル評価に特化したノード
"""

from typing import Dict, Optional
import google.generativeai as genai

from .base import BaseNode, ResearchState, ScoreDetail
from ..utils.evaluation_formatters import EvaluationFormatters
from ..utils.evaluation_parser import EvaluationParser
from ..prompts.scoring_criteria import ScoringCriteria, WeightProfile


class SkillEvaluatorNode(BaseNode):
    """スキル（必須要件・歓迎要件）の評価に特化したノード"""
    
    def __init__(self, api_key: str):
        super().__init__("SkillEvaluator")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash')
    
    async def process(self, state: ResearchState) -> ResearchState:
        """スキルの評価を実行"""
        self.state = "processing"
        
        print(f"  スキル評価を開始（サイクル{state.current_cycle}）")
        
        # 構造化データの取得
        has_structured_job_data = hasattr(state, 'structured_job_data') and state.structured_job_data
        structured_job_data_text = EvaluationFormatters.format_structured_job_data(state) if has_structured_job_data else ''
        
        has_structured_resume_data = hasattr(state, 'structured_resume_data') and state.structured_resume_data
        structured_resume_data_text = EvaluationFormatters.format_structured_resume_data(state) if has_structured_resume_data else ''
        
        # 候補者情報を取得
        candidate_info = await EvaluationFormatters.get_candidate_info(state)
        
        prompt = f"""あなたは経験豊富な採用コンサルタントです。
候補者のスキル評価を行ってください。

# 評価ルール
1. 構造化データを最優先で使用
2. 必須要件と歓迎要件を明確に区別
3. スキルの類似性・関連性を適切に評価

# 入力データ
## 候補者レジュメ
{state.resume}

## 候補者情報
{candidate_info}

{structured_resume_data_text}

{structured_job_data_text}

## 求人票（構造化データで判断できない場合の参照用）
{state.job_description or ""}

# 評価基準
## 必須要件（必須スキル・required_skills）
- 候補者が持っていなければならない要件
- 1つでも未充足があれば大幅減点
- 類似経験は部分点として評価（同一業界80%、類似業界60%、異業界40%）

## 歓迎要件（歓迎スキル・preferred_skills）
- あればプラスになる要件
- 不足していても減点はしない
- 1つ充足ごとに加点

# 出力フォーマット
## 必須要件評価
評価点: [0-45]
詳細:
- [各必須スキル]: [充足/類似/不足] - [根拠となるレジュメの記載]

## 歓迎要件評価
評価点: [0-15]
詳細:
- [各歓迎スキル]: [充足/不足] - [該当する経験があれば記載]

## 総合スキル評価
- 必須要件の充足度: [パーセント]%
- 歓迎要件の充足度: [パーセント]%
- 特筆すべきスキル: [あれば記載]
- スキル面での懸念点: [必須要件の不足のみ記載]"""

        print(f"  LLMにスキル評価プロンプト送信中...")
        response = self.model.generate_content(prompt)
        
        # 評価結果をパース
        skill_scores = self._parse_skill_scores(response.text)
        
        # 状態を更新
        if not hasattr(state, 'partial_scores'):
            state.partial_scores = {}
        state.partial_scores['skills'] = skill_scores
        
        self.state = "completed"
        return state
    
    def _parse_skill_scores(self, response_text: str) -> Dict[str, ScoreDetail]:
        """スキル評価結果をパース"""
        scores = {}
        
        # 必須要件の評価点を抽出
        required_score = EvaluationParser.parse_score(response_text, "必須要件評価", "評価点")
        if required_score is not None:
            scores['required_skills'] = ScoreDetail(
                category="必須要件",
                actual_score=required_score,
                max_score=45,
                items=[],
                reasoning=self._extract_section(response_text, "必須要件評価", "詳細")
            )
        
        # 歓迎要件の評価点を抽出
        preferred_score = EvaluationParser.parse_score(response_text, "歓迎要件評価", "評価点")
        if preferred_score is not None:
            scores['preferred_skills'] = ScoreDetail(
                category="歓迎要件",
                actual_score=preferred_score,
                max_score=15,
                items=[],
                reasoning=self._extract_section(response_text, "歓迎要件評価", "詳細")
            )
        
        return scores
    
    def _extract_section(self, text: str, section: str, subsection: str) -> str:
        """特定セクションの内容を抽出"""
        import re
        
        # セクション開始位置を探す
        pattern = rf"#+ {section}.*?\n.*?{subsection}:(.*?)(?=\n#|\Z)"
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        
        if match:
            return match.group(1).strip()
        return ""