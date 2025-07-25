"""
組織適合性と突出した経歴の評価に特化したノード
"""

from typing import Dict, Optional
import google.generativeai as genai

from .base import BaseNode, ResearchState, ScoreDetail
from ..utils.evaluation_formatters import EvaluationFormatters
from ..utils.evaluation_parser import EvaluationParser


class FitEvaluatorNode(BaseNode):
    """組織適合性と突出した経歴の評価に特化したノード"""
    
    def __init__(self, api_key: str):
        super().__init__("FitEvaluator")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash')
    
    async def process(self, state: ResearchState) -> ResearchState:
        """組織適合性と突出した経歴の評価を実行"""
        self.state = "processing"
        
        print(f"  組織適合性・突出経歴評価を開始（サイクル{state.current_cycle}）")
        
        # 候補者情報を取得
        candidate_info = await EvaluationFormatters.get_candidate_info(state)
        
        # 構造化データの取得
        has_structured_job_data = hasattr(state, 'structured_job_data') and state.structured_job_data
        structured_job_data_text = EvaluationFormatters.format_structured_job_data(state) if has_structured_job_data else ''
        
        # RAG洞察のフォーマット
        rag_insights_text = EvaluationFormatters.format_rag_insights(state)
        
        prompt = f"""あなたは経験豊富な採用コンサルタントです。
候補者の組織適合性と突出した経歴を評価してください。

# 評価ルール
1. 過去の実績から組織適合性を判断（ポテンシャルではなく実績ベース）
2. 求人に活かせる希少な経歴のみを突出した経歴として評価
3. 企業規模の適応性を重視

# 入力データ
## 候補者レジュメ
{state.resume}

## 候補者情報
{candidate_info}

{structured_job_data_text}

## 求人票
{state.job_description or ""}

{rag_insights_text}

# 評価基準
## 組織適合性（10点満点）
- 過去の所属企業と求人企業の類似性（業界、規模、文化）
- 実際の転職実績（成功した環境変化の経験）
- 企業規模適応性（規模差による減点：2段階差で-5点、3段階以上で-10点）
- ポテンシャルや適応可能性ではなく、過去の実績から判断

### 企業規模の段階
1. スタートアップ（〜50名）
2. 中小企業（50〜300名）
3. 中堅企業（300〜1000名）
4. 大企業（1000名〜）

## 突出した経歴・実績（5点満点）
- 必須要件の不足を補う「尖った経歴」（ボーナス要素）
- 求人に関連する分野での業界注目度
- 求人に活かせる希少経験
- 求人領域での圧倒的成果
- 重要：求人との関連性がない経歴は評価しない

# 出力フォーマット
## 組織適合性評価
評価点: [0-10]

### 企業規模適応
- 過去の所属企業規模: [リスト]
- 求人企業規模: [規模]
- 規模差評価: [点数]/5点

### 文化・環境適合
- 業界経験の一致度: [点数]/3点
- 組織文化の類似性: [点数]/2点

### 適合性の詳細
- [具体的な適合要素や懸念点]

## 突出した経歴評価
評価点: [0-5]

### 希少価値のある経歴
- [該当する経歴]: [なぜ希少か、求人にどう活かせるか]

### 業界での注目度
- [該当する実績]: [業界での位置づけ]

### 総合評価
- 組織への適応可能性: [高/中/低]（過去実績ベース）
- 突出要素による付加価値: [ある/なし]"""

        print(f"  LLMに組織適合性評価プロンプト送信中...")
        response = self.model.generate_content(prompt)
        
        # 評価結果をパース
        fit_scores = self._parse_fit_scores(response.text)
        
        # 状態を更新
        if not hasattr(state, 'partial_scores'):
            state.partial_scores = {}
        state.partial_scores.update(fit_scores)
        
        self.state = "completed"
        return state
    
    def _parse_fit_scores(self, response_text: str) -> Dict[str, ScoreDetail]:
        """組織適合性評価結果をパース"""
        scores = {}
        
        # 組織適合性の評価点を抽出
        org_score = EvaluationParser.parse_score(response_text, "組織適合性評価", "評価点")
        if org_score is not None:
            scores['organizational_fit'] = ScoreDetail(
                category="組織適合性",
                actual_score=org_score,
                max_score=10,
                items=[],
                reasoning=self._extract_section(response_text, "組織適合性評価", "適合性の詳細")
            )
        
        # 突出した経歴の評価点を抽出
        outstanding_score = EvaluationParser.parse_score(response_text, "突出した経歴評価", "評価点")
        if outstanding_score is not None:
            scores['outstanding_career'] = ScoreDetail(
                category="突出した経歴",
                actual_score=outstanding_score,
                max_score=5,
                items=[],
                reasoning=self._extract_section(response_text, "突出した経歴評価", "希少価値のある経歴")
            )
        
        return scores
    
    def _extract_section(self, text: str, section: str, subsection: str) -> str:
        """特定セクションの内容を抽出"""
        import re
        
        # セクション開始位置を探す
        pattern = rf"#+ {section}.*?\n.*?{subsection}(.*?)(?=\n#|\Z)"
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        
        if match:
            return match.group(1).strip()
        return ""