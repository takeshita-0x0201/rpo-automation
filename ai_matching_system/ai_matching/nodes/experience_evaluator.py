"""
実務経験評価に特化したノード
"""

from typing import Dict, Optional
import google.generativeai as genai

from .base import BaseNode, ResearchState, ScoreDetail
from ..utils.evaluation_formatters import EvaluationFormatters
from ..utils.evaluation_parser import EvaluationParser


class ExperienceEvaluatorNode(BaseNode):
    """実務遂行能力の評価に特化したノード"""
    
    def __init__(self, api_key: str):
        super().__init__("ExperienceEvaluator")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
    
    async def process(self, state: ResearchState) -> ResearchState:
        """実務経験の評価を実行"""
        self.state = "processing"
        
        print(f"  実務経験評価を開始（サイクル{state.current_cycle}）")
        
        # 追加情報のフォーマット
        additional_info = EvaluationFormatters.format_additional_info(state.search_results)
        
        # 候補者情報を取得
        candidate_info = await EvaluationFormatters.get_candidate_info(state)
        
        # 構造化データの取得
        has_structured_job_data = hasattr(state, 'structured_job_data') and state.structured_job_data
        structured_job_data_text = EvaluationFormatters.format_structured_job_data(state) if has_structured_job_data else ''
        
        prompt = f"""あなたは経験豊富な採用コンサルタントです。
候補者の実務遂行能力を評価してください。

# 評価ルール
1. 求人に関連する実務経験の深さと実績を評価
2. 具体的な成果・数値実績を重視
3. 経験の直近性を考慮

# 入力データ
## 候補者レジュメ
{state.resume}

## 候補者情報
{candidate_info}

{structured_job_data_text}

## 求人票
{state.job_description or ""}

## 追加情報
{state.job_memo or ""}
{additional_info}

# 評価基準
## 実務遂行能力（25点満点）
- 求人に関連する実務経験の深さ
- 具体的な成果・数値実績
- 直近の経験を高く評価（3年以内100%、5年以内80%、10年以内60%）
- 求人との関連性：直接関連100%、間接関連60%、関連薄40%

# 時間経過による評価の減衰
- 直近3年以内：100%評価
- 3-5年前：80%評価
- 5-10年前：60%評価
- 10年以上前：40%評価

# 出力フォーマット
## 実務遂行能力評価
評価点: [0-25]

### 関連実務経験
- [経験内容]: [評価点]/[配点] - [時期と期間]
- 関連性: [直接/間接/薄い]
- 具体的実績: [数値実績や成果]

### 経験の直近性
- 最も関連性の高い経験: [○年前]
- 直近性による評価係数: [パーセント]%

### 実績・成果
- 定量的成果: [売上、効率化、コスト削減等の数値]
- 定性的成果: [プロジェクト成功、表彰等]

### 総合評価
- 求人要件との実務経験マッチ度: [高/中/低]
- 即戦力度: [パーセント]%
- 実務面での強み: [箇条書き]"""

        print(f"  LLMに実務経験評価プロンプト送信中...")
        response = self.model.generate_content(prompt)
        
        # 評価結果をパース
        experience_score = self._parse_experience_score(response.text)
        
        # 状態を更新
        if not hasattr(state, 'partial_scores'):
            state.partial_scores = {}
        state.partial_scores['experience'] = experience_score
        
        self.state = "completed"
        return state
    
    def _parse_experience_score(self, response_text: str) -> ScoreDetail:
        """実務経験評価結果をパース"""
        score = EvaluationParser.parse_score(response_text, "実務遂行能力評価", "評価点")
        
        return ScoreDetail(
            category="実務遂行能力",
            actual_score=score if score is not None else 0,
            max_score=25,
            items=[],
            reasoning=response_text  # 詳細な評価内容を保存
        )