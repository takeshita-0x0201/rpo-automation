"""
セマンティックスキルマッチャー
LLMを使用してスキルの意味的類似性を判定
"""

import os
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import google.generativeai as genai
from functools import lru_cache
import hashlib
import json


@dataclass
class SkillMatchResult:
    """スキルマッチング結果"""
    required_skill: str
    matched_candidate_skill: Optional[str]
    match_score: float  # 0.0-1.0
    reasoning: str
    is_match: bool


@dataclass
class RoleRelevanceResult:
    """役職関連性の判定結果"""
    is_relevant: bool
    relevance_score: float  # 0.0-1.0
    matched_aspects: List[str]
    reasoning: str


class SemanticSkillMatcher:
    """LLMを使用したセマンティックスキルマッチング"""
    
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash')
        self._cache = {}  # シンプルなメモリキャッシュ
    
    def _get_cache_key(self, skill1: str, skill2: str) -> str:
        """キャッシュキーを生成"""
        combined = f"{skill1.lower()}|{skill2.lower()}"
        return hashlib.md5(combined.encode()).hexdigest()
    
    async def match_skills_batch(self, 
                                required_skills: List[str], 
                                candidate_skills: List[str]) -> List[SkillMatchResult]:
        """バッチでスキルマッチングを実行"""
        
        # キャッシュから既存の結果を取得
        results = []
        uncached_pairs = []
        
        for req_skill in required_skills:
            cached_result = None
            for cand_skill in candidate_skills:
                cache_key = self._get_cache_key(req_skill, cand_skill)
                if cache_key in self._cache:
                    cached_result = self._cache[cache_key]
                    break
            
            if cached_result:
                results.append(cached_result)
            else:
                uncached_pairs.append((req_skill, candidate_skills))
        
        # キャッシュにない項目をバッチでLLMに問い合わせ
        if uncached_pairs:
            new_results = await self._batch_evaluate_skills(uncached_pairs)
            results.extend(new_results)
            
            # キャッシュに保存
            for result in new_results:
                if result.matched_candidate_skill:
                    cache_key = self._get_cache_key(
                        result.required_skill, 
                        result.matched_candidate_skill
                    )
                    self._cache[cache_key] = result
        
        return results
    
    async def _batch_evaluate_skills(self, 
                                   skill_pairs: List[Tuple[str, List[str]]]) -> List[SkillMatchResult]:
        """バッチでスキルを評価"""
        
        prompt = """あなたは採用のプロフェッショナルです。
求人で求められるスキルと候補者のスキルの類似性を評価してください。

# 評価基準
1. **完全一致（1.0）**: 同じスキルまたは同義語
   - 例: "法人営業" = "B2B営業" = "企業向け営業"
   - 例: "Python" = "Python3" = "Python開発"

2. **高い類似性（0.8-0.9）**: 実質的に同じスキル
   - 例: "営業経験" ≈ "新規開拓営業" ≈ "アカウント営業"
   - 例: "マネジメント" ≈ "チームリード" ≈ "部下指導"

3. **中程度の類似性（0.6-0.7）**: 関連性の高いスキル
   - 例: "財務" ≈ "経理" ≈ "管理会計"
   - 例: "JavaScript" ≈ "TypeScript" ≈ "フロントエンド開発"

4. **低い類似性（0.3-0.5）**: 部分的に関連
   - 例: "営業" ≈ "カスタマーサクセス" ≈ "顧客対応"
   - 例: "Java" ≈ "C#" ≈ "オブジェクト指向言語"

5. **関連なし（0.0-0.2）**: 異なるスキル
   - 例: "営業" ≠ "エンジニア"
   - 例: "Python" ≠ "営業"

# 入力データ
以下の必須スキルと候補者スキルを評価してください：

"""
        
        # 各ペアを追加
        for i, (req_skill, cand_skills) in enumerate(skill_pairs):
            prompt += f"\n## 評価{i+1}\n"
            prompt += f"必須スキル: {req_skill}\n"
            prompt += f"候補者スキル: {', '.join(cand_skills)}\n"
        
        prompt += """
# 出力フォーマット
各評価について、以下のJSON形式で出力してください：
```json
[
  {
    "required_skill": "必須スキル",
    "matched_candidate_skill": "最も類似した候補者スキル（ない場合はnull）",
    "match_score": 0.0-1.0の数値,
    "reasoning": "判定理由",
    "is_match": true/false（0.3以上でtrue）
  }
]
```
"""
        
        try:
            response = self.model.generate_content(prompt)
            response_text = response.text
            
            # JSONを抽出
            import re
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response_text)
            if json_match:
                json_text = json_match.group(1)
                evaluations = json.loads(json_text)
                
                results = []
                for eval_data in evaluations:
                    results.append(SkillMatchResult(
                        required_skill=eval_data["required_skill"],
                        matched_candidate_skill=eval_data["matched_candidate_skill"],
                        match_score=float(eval_data["match_score"]),
                        reasoning=eval_data["reasoning"],
                        is_match=eval_data["is_match"]
                    ))
                
                return results
            else:
                # フォールバック: 空の結果を返す
                return [
                    SkillMatchResult(
                        required_skill=req_skill,
                        matched_candidate_skill=None,
                        match_score=0.0,
                        reasoning="評価に失敗しました",
                        is_match=False
                    )
                    for req_skill, _ in skill_pairs
                ]
                
        except Exception as e:
            print(f"[SemanticSkillMatcher] エラー: {e}")
            # エラー時は空の結果を返す
            return [
                SkillMatchResult(
                    required_skill=req_skill,
                    matched_candidate_skill=None,
                    match_score=0.0,
                    reasoning=f"エラー: {str(e)}",
                    is_match=False
                )
                for req_skill, _ in skill_pairs
            ]
    
    async def evaluate_role_relevance(self,
                                    required_experience: str,
                                    candidate_role: str,
                                    candidate_description: str) -> RoleRelevanceResult:
        """役職・業務内容の関連性を評価"""
        
        # キャッシュチェック
        cache_key = self._get_cache_key(required_experience, f"{candidate_role}|{candidate_description}")
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        prompt = f"""あなたは採用のプロフェッショナルです。
求人で求められる経験と候補者の役職・業務内容の関連性を評価してください。

# 求められる経験
{required_experience}

# 候補者の情報
役職: {candidate_role}
業務内容: {candidate_description[:500]}...  # 長すぎる場合は切り詰め

# 評価基準
1. **役職の類似性**
   - "営業部長" ≈ "セールスマネージャー" ≈ "営業責任者"
   - "エンジニア" ≈ "開発者" ≈ "プログラマー"
   - "企画" ≈ "戦略" ≈ "事業開発"

2. **業務内容の本質的な一致**
   - 「新規開拓」「顧客獲得」「案件創出」→ 営業活動
   - 「チーム統括」「部下育成」「目標管理」→ マネジメント
   - 「要件定義」「設計」「実装」→ 開発業務

3. **経験レベルの一致**
   - 管理職経験の有無
   - 責任範囲の類似性
   - 成果・実績のレベル

# 出力フォーマット
以下のJSON形式で出力してください：
```json
{{
  "is_relevant": true/false,
  "relevance_score": 0.0-1.0の数値,
  "matched_aspects": ["一致する要素1", "一致する要素2"],
  "reasoning": "判定理由"
}}
```
"""
        
        try:
            response = self.model.generate_content(prompt)
            response_text = response.text
            
            # JSONを抽出
            import re
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response_text)
            if json_match:
                json_text = json_match.group(1)
                eval_data = json.loads(json_text)
                
                result = RoleRelevanceResult(
                    is_relevant=eval_data["is_relevant"],
                    relevance_score=float(eval_data["relevance_score"]),
                    matched_aspects=eval_data["matched_aspects"],
                    reasoning=eval_data["reasoning"]
                )
                
                # キャッシュに保存
                self._cache[cache_key] = result
                
                return result
            else:
                # フォールバック
                return RoleRelevanceResult(
                    is_relevant=False,
                    relevance_score=0.0,
                    matched_aspects=[],
                    reasoning="評価に失敗しました"
                )
                
        except Exception as e:
            print(f"[SemanticSkillMatcher] 役職評価エラー: {e}")
            return RoleRelevanceResult(
                is_relevant=False,
                relevance_score=0.0,
                matched_aspects=[],
                reasoning=f"エラー: {str(e)}"
            )
    
    def clear_cache(self):
        """キャッシュをクリア"""
        self._cache.clear()
    
    def get_cache_stats(self) -> Dict[str, int]:
        """キャッシュ統計を取得"""
        return {
            "cache_size": len(self._cache),
            "memory_usage_bytes": sum(
                len(str(k)) + len(str(v)) 
                for k, v in self._cache.items()
            )
        }