"""
キャリア継続性分析器 V2
LLMベースの一括評価でシンプル化
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import os
import json
import re

from .semantic_skill_matcher import SemanticSkillMatcher


@dataclass
class ContinuityAssessmentV2:
    """継続性評価V2"""
    has_recent_relevant_experience: bool
    months_since_relevant_experience: Optional[int]
    career_change_detected: bool
    department_change_detected: bool
    skill_retention_score: float  # 0.0-1.0
    penalty_score: float  # 0.0-1.0 (減点率)
    explanation: str
    recommendations: List[str]
    career_timeline: List[Dict]  # 職歴タイムライン


class CareerContinuityAnalyzerV2:
    """キャリア継続性分析器V2 - LLMベースのシンプル実装"""
    
    def __init__(self, use_llm: bool = True, gemini_api_key: Optional[str] = None):
        # LLMベースのスキルマッチャーを初期化
        self.use_llm = use_llm
        if use_llm:
            if not gemini_api_key:
                gemini_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_GEMINI_API_KEY")
            if gemini_api_key:
                self.skill_matcher = SemanticSkillMatcher(gemini_api_key)
            else:
                print("[CareerContinuityAnalyzerV2] 警告: Gemini APIキーが設定されていません。")
                self.use_llm = False
                self.skill_matcher = None
        else:
            self.skill_matcher = None
        
        # ペナルティ設定（転職市場の実態に基づいて調整）
        # 参考：転職活動期間は平均3ヶ月、3-6ヶ月は一般的
        self.penalty_thresholds = {
            "no_gap": 0.0,          # ブランクなし
            "normal_gap": 0.0,      # 1-3ヶ月（通常の転職活動期間）
            "short_gap": 0.05,      # 4-6ヶ月（やや長いが許容範囲）
            "medium_gap": 0.1,      # 7-12ヶ月（説明が必要）
            "long_gap": 0.15,       # 13-24ヶ月（要確認）
            "very_long_gap": 0.2    # 25ヶ月以上（詳細な確認必要）
        }
    
    async def analyze_career_continuity(self,
                                      resume_text: str,
                                      required_skills: List[str],
                                      required_experience: str) -> ContinuityAssessmentV2:
        """キャリアの継続性を分析（一括評価版）"""
        
        if self.use_llm and self.skill_matcher:
            # LLMで一括評価
            return await self._analyze_with_llm(
                resume_text, required_skills, required_experience
            )
        else:
            # フォールバック：簡易評価
            return self._analyze_simple(
                resume_text, required_skills, required_experience
            )
    
    async def _analyze_with_llm(self,
                              resume_text: str,
                              required_skills: List[str],
                              required_experience: str) -> ContinuityAssessmentV2:
        """LLMを使用して一括でキャリア継続性を分析"""
        
        prompt = f"""あなたは経験豊富な採用コンサルタントです。
候補者のキャリア継続性を分析してください。

# 重要な前提
- 転職活動期間は平均3ヶ月、3-6ヶ月のブランクは一般的で問題ない
- 転用可能スキル（Transferable Skills）を重視する
- キャリアチェンジは必ずしもネガティブではない（スキルの転用可能性を評価）
- 93%の雇用主がソフトスキルを重視している

# 候補者のレジュメ
{resume_text}

# 求められる要件
## 必須スキル
{', '.join(required_skills)}

## 求められる経験
{required_experience}

# 分析項目
以下の項目を分析し、JSON形式で出力してください：

1. **職歴タイムライン**
   - 各職歴の会社名、役職、期間、主な業務内容を抽出
   - 求める要件との関連性を判定（直接的な関連性だけでなく、転用可能なスキルも考慮）

2. **直近の関連経験**
   - 求める要件に関連する最新の職歴を特定
   - 現在からのブランク期間（月数）を計算

3. **キャリアチェンジ検出**
   - 業界や職種の変更があるか（ポジティブ・ネガティブ両面を評価）
   - 転用可能なスキルの有無と活用可能性

4. **スキル保持評価**
   - 転用可能スキル（コミュニケーション、問題解決、リーダーシップ等）の評価
   - 技術的スキルの保持率（0.0-1.0）
   - ブランク期間中の自己啓発活動

5. **推奨事項**
   - 強みとして活かせる転用可能スキル
   - 面接で確認すべき点
   - 必要に応じたキャッチアップ方法

# 出力形式
```json
{{
  "career_timeline": [
    {{
      "company": "会社名",
      "role": "役職",
      "start_date": "YYYY-MM",
      "end_date": "YYYY-MM or null（現在）",
      "responsibilities": ["業務1", "業務2"],
      "is_relevant": true/false,
      "relevance_reason": "関連性の理由"
    }}
  ],
  "has_recent_relevant_experience": true/false,
  "months_since_relevant_experience": 数値またはnull,
  "career_change_detected": true/false,
  "career_change_details": "詳細（ある場合）",
  "department_change_detected": true/false,
  "skill_retention_score": 0.0-1.0,
  "skill_retention_reason": "スコアの根拠",
  "recommendations": ["推奨1", "推奨2"],
  "overall_assessment": "総合評価"
}}
```
"""
        
        try:
            response = self.skill_matcher.model.generate_content(prompt)
            response_text = response.text
            
            # JSONを抽出
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response_text)
            if json_match:
                json_text = json_match.group(1)
                data = json.loads(json_text)
                
                # ペナルティスコアを計算
                months_gap = data.get('months_since_relevant_experience')
                penalty = self._calculate_penalty(
                    months_gap,
                    data.get('career_change_detected', False),
                    data.get('department_change_detected', False),
                    data.get('skill_retention_score', 0.5)
                )
                
                return ContinuityAssessmentV2(
                    has_recent_relevant_experience=data.get('has_recent_relevant_experience', False),
                    months_since_relevant_experience=months_gap,
                    career_change_detected=data.get('career_change_detected', False),
                    department_change_detected=data.get('department_change_detected', False),
                    skill_retention_score=data.get('skill_retention_score', 0.5),
                    penalty_score=penalty,
                    explanation=data.get('overall_assessment', ''),
                    recommendations=data.get('recommendations', []),
                    career_timeline=data.get('career_timeline', [])
                )
            else:
                # JSON抽出失敗時のフォールバック
                return self._create_default_assessment()
                
        except Exception as e:
            print(f"[CareerContinuityAnalyzerV2] LLM評価エラー: {e}")
            return self._create_default_assessment()
    
    def _analyze_simple(self,
                       resume_text: str,
                       required_skills: List[str],
                       required_experience: str) -> ContinuityAssessmentV2:
        """簡易的な分析（フォールバック）"""
        
        # 簡単なキーワードチェック
        has_relevant = any(
            skill.lower() in resume_text.lower() 
            for skill in required_skills
        )
        
        # キャリアチェンジの検出
        career_change_keywords = ["転職", "キャリアチェンジ", "業界変更", "未経験"]
        career_change = any(
            keyword in resume_text 
            for keyword in career_change_keywords
        )
        
        return ContinuityAssessmentV2(
            has_recent_relevant_experience=has_relevant,
            months_since_relevant_experience=0 if has_relevant else None,
            career_change_detected=career_change,
            department_change_detected=False,
            skill_retention_score=1.0 if has_relevant else 0.5,
            penalty_score=0.0 if has_relevant else 0.2,
            explanation="簡易評価モードで実行",
            recommendations=["詳細な職歴確認が必要"],
            career_timeline=[]
        )
    
    def _calculate_penalty(self,
                         months_gap: Optional[int],
                         career_change: bool,
                         dept_change: bool,
                         skill_retention: float) -> float:
        """ペナルティを計算"""
        penalty = 0.0
        
        # ブランク期間によるペナルティ
        if months_gap is None:
            penalty = 0.3  # 関連経験がない（50%から30%に緩和）
        elif months_gap <= 0:
            penalty = self.penalty_thresholds["no_gap"]
        elif months_gap <= 3:
            penalty = self.penalty_thresholds["normal_gap"]  # 3ヶ月以内は正常
        elif months_gap <= 6:
            penalty = self.penalty_thresholds["short_gap"]
        elif months_gap <= 12:
            penalty = self.penalty_thresholds["medium_gap"]
        elif months_gap <= 24:
            penalty = self.penalty_thresholds["long_gap"]
        else:
            penalty = self.penalty_thresholds["very_long_gap"]
        
        # キャリアチェンジによる追加ペナルティ（転用可能スキルを考慮して緩和）
        if career_change:
            # スキル保持率が高い場合はペナルティを軽減
            base_penalty = 0.1  # 15%から10%に基本ペナルティを緩和
            skill_adjustment = (1 - skill_retention) * 0.05  # スキル保持率に応じて最大5%追加
            penalty += base_penalty + skill_adjustment
        
        # 部署異動による追加ペナルティ（軽度）
        if dept_change and not career_change:
            penalty += 0.03  # 5%から3%に緩和
        
        # スキル保持率による調整
        penalty *= (2 - skill_retention)  # スキル保持率が低いほどペナルティ増
        
        return min(penalty, 0.5)  # 最大50%減点
    
    def _create_default_assessment(self) -> ContinuityAssessmentV2:
        """デフォルトの評価を作成"""
        return ContinuityAssessmentV2(
            has_recent_relevant_experience=False,
            months_since_relevant_experience=None,
            career_change_detected=False,
            department_change_detected=False,
            skill_retention_score=0.5,
            penalty_score=0.2,
            explanation="評価を完了できませんでした",
            recommendations=["職歴の詳細確認が必要"],
            career_timeline=[]
        )
    
    def format_continuity_report(self, assessment: ContinuityAssessmentV2) -> str:
        """継続性評価レポートをフォーマット"""
        lines = []
        lines.append("# キャリア継続性評価")
        
        # サマリー
        lines.append("\n## サマリー")
        if assessment.has_recent_relevant_experience:
            lines.append("✅ 直近に関連経験あり")
        else:
            lines.append("⚠️ 直近の関連経験なし")
        
        if assessment.career_change_detected:
            lines.append("🔄 キャリアチェンジあり")
        
        if assessment.department_change_detected:
            lines.append("🔀 部署異動あり")
        
        # 詳細
        lines.append("\n## 詳細")
        if assessment.months_since_relevant_experience is not None:
            lines.append(f"- 関連経験からの経過: {assessment.months_since_relevant_experience}ヶ月")
        else:
            lines.append("- 関連経験からの経過: 計測不可")
        
        lines.append(f"- スキル保持率: {assessment.skill_retention_score:.0%}")
        lines.append(f"- ペナルティスコア: {assessment.penalty_score:.0%}")
        
        # 職歴タイムライン
        if assessment.career_timeline:
            lines.append("\n## 職歴タイムライン")
            for career in assessment.career_timeline:
                period = f"{career.get('start_date', '不明')} - {career.get('end_date', '現在')}"
                lines.append(f"\n### {period}: {career.get('company', '不明')} - {career.get('role', '不明')}")
                if career.get('is_relevant'):
                    lines.append(f"✅ 関連あり: {career.get('relevance_reason', '')}")
                else:
                    lines.append("❌ 関連なし")
        
        # 説明
        lines.append("\n## 評価")
        lines.append(assessment.explanation)
        
        # 推奨事項
        if assessment.recommendations:
            lines.append("\n## 推奨事項")
            for rec in assessment.recommendations:
                lines.append(f"- {rec}")
        
        return '\n'.join(lines)