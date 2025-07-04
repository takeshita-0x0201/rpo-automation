"""
AI評価処理
OpenAI APIを使用して候補者を評価
"""
import os
import logging
from typing import Dict, Any
import openai
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

class AIEvaluator:
    """AI評価を処理するクラス"""
    
    def __init__(self):
        self.openai_client = openai.OpenAI(
            api_key=os.getenv("OPENAI_API_KEY")
        )
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def evaluate_candidate(
        self,
        candidate: Dict[str, Any],
        requirement: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        候補者を採用要件に対して評価
        
        Args:
            candidate: 候補者情報
            requirement: 採用要件
            
        Returns:
            評価結果
        """
        try:
            # プロンプトの構築
            prompt = self._build_evaluation_prompt(candidate, requirement)
            
            # OpenAI APIの呼び出し
            response = self.openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {
                        "role": "system",
                        "content": "あなたは経験豊富な採用コンサルタントです。候補者と採用要件のマッチング度を評価してください。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            # 評価結果の解析
            evaluation_text = response.choices[0].message.content
            
            # スコアとサマリーの抽出（簡易実装）
            score = self._extract_score(evaluation_text)
            summary = self._extract_summary(evaluation_text)
            
            return {
                "score": score,
                "summary": summary,
                "detailed_evaluation": evaluation_text,
                "evaluated_at": os.environ.get("FUNCTION_TIMESTAMP", "")
            }
            
        except Exception as e:
            logger.error(f"Error evaluating candidate: {str(e)}")
            # エラー時はデフォルト評価を返す
            return {
                "score": 50,
                "summary": "評価エラーが発生しました",
                "detailed_evaluation": str(e),
                "evaluated_at": os.environ.get("FUNCTION_TIMESTAMP", "")
            }
    
    def _build_evaluation_prompt(
        self,
        candidate: Dict[str, Any],
        requirement: Dict[str, Any]
    ) -> str:
        """評価用プロンプトを構築"""
        return f"""
以下の候補者情報と採用要件を比較し、マッチング度を評価してください。

【採用要件】
- ポジション: {requirement.get('position', 'N/A')}
- 必須スキル: {', '.join(requirement.get('required_skills', []))}
- 歓迎スキル: {', '.join(requirement.get('preferred_skills', []))}
- 必要経験年数: {requirement.get('experience_years', 'N/A')}年以上
- 求める人物像: {requirement.get('description', 'N/A')}

【候補者情報】
- 名前: {candidate.get('name', 'N/A')}
- 現在の役職: {candidate.get('title', 'N/A')}
- 所属企業: {candidate.get('company', 'N/A')}
- 経験年数: {candidate.get('experience_years', 'N/A')}年
- スキル: {', '.join(candidate.get('skills', []))}
- 学歴: {candidate.get('education', 'N/A')}

以下の形式で評価してください：

1. マッチング度スコア（0-100点）: [スコア]
2. 評価サマリー（1-2文）: [サマリー]
3. 詳細評価:
   - 強み: [候補者の強み]
   - 懸念点: [懸念される点]
   - 総合評価: [総合的な評価]
"""
    
    def _extract_score(self, evaluation_text: str) -> int:
        """評価テキストからスコアを抽出"""
        import re
        
        # スコアのパターンを検索
        score_pattern = r'マッチング度スコア[^:：]*[:：]\s*(\d+)'
        match = re.search(score_pattern, evaluation_text)
        
        if match:
            return int(match.group(1))
        
        # 見つからない場合はデフォルト値
        return 70
    
    def _extract_summary(self, evaluation_text: str) -> str:
        """評価テキストからサマリーを抽出"""
        import re
        
        # サマリーのパターンを検索
        summary_pattern = r'評価サマリー[^:：]*[:：]\s*([^\n]+)'
        match = re.search(summary_pattern, evaluation_text)
        
        if match:
            return match.group(1).strip()
        
        # 見つからない場合は最初の文を返す
        lines = evaluation_text.strip().split('\n')
        for line in lines:
            if line.strip():
                return line.strip()[:100]
        
        return "評価サマリーを取得できませんでした"