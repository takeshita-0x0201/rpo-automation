"""
キャリア継続性分析器
求める経験に対して、直近のキャリアチェンジや異動によるブランクを評価
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import re
import asyncio
import os

from .semantic_skill_matcher import SemanticSkillMatcher, SkillMatchResult, RoleRelevanceResult


@dataclass
class CareerPeriod:
    """キャリア期間"""
    role: str
    company: str
    department: Optional[str]
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    skills: List[str]
    is_relevant: bool  # 求める経験との関連性


@dataclass
class ContinuityAssessment:
    """継続性評価"""
    has_recent_relevant_experience: bool
    months_since_relevant_experience: Optional[int]
    career_change_detected: bool
    department_change_detected: bool
    skill_retention_score: float  # 0.0-1.0
    penalty_score: float  # 0.0-1.0 (減点率)
    explanation: str
    recommendations: List[str]


class CareerContinuityAnalyzer:
    """キャリア継続性分析器"""
    
    def __init__(self, use_llm: bool = True, gemini_api_key: Optional[str] = None):
        # スキルの陳腐化率（月あたり）
        self.skill_decay_rate = 0.02  # 毎月2%スキルが劣化
        
        # ペナルティ設定
        self.penalty_thresholds = {
            "no_gap": 0.0,          # ブランクなし
            "short_gap": 0.1,       # 1-6ヶ月
            "medium_gap": 0.2,      # 7-12ヶ月
            "long_gap": 0.3,        # 13-24ヶ月
            "very_long_gap": 0.4    # 25ヶ月以上
        }
        
        # キャリアチェンジの指標
        self.career_change_indicators = [
            "転職", "キャリアチェンジ", "業界変更", "職種変更",
            "未経験", "新しい分野", "ジョブチェンジ"
        ]
        
        # 部署異動の指標
        self.department_change_indicators = [
            "異動", "配属変更", "部署移動", "ローテーション",
            "出向", "転籍"
        ]
        
        # LLMベースのスキルマッチャーを初期化
        self.use_llm = use_llm
        if use_llm:
            if not gemini_api_key:
                gemini_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_GEMINI_API_KEY")
            if gemini_api_key:
                self.skill_matcher = SemanticSkillMatcher(gemini_api_key)
            else:
                print("[CareerContinuityAnalyzer] 警告: Gemini APIキーが設定されていません。従来のマッチングに切り替えます。")
                self.use_llm = False
                self.skill_matcher = None
        else:
            self.skill_matcher = None
    
    async def analyze_career_continuity(self,
                                resume_text: str,
                                required_skills: List[str],
                                required_experience: str) -> ContinuityAssessment:
        """キャリアの継続性を分析"""
        
        # 職歴を抽出
        career_timeline = self._extract_career_timeline(resume_text)
        
        # 求める経験との関連性を評価
        for period in career_timeline:
            period.is_relevant = await self._is_experience_relevant(
                period, required_skills, required_experience
            )
        
        # 最新の関連経験を特定
        latest_relevant = self._find_latest_relevant_experience(career_timeline)
        
        # キャリアチェンジ/異動を検出
        career_change = self._detect_career_change(resume_text, career_timeline)
        dept_change = self._detect_department_change(resume_text, career_timeline)
        
        # ブランク期間を計算
        months_gap = self._calculate_experience_gap(latest_relevant)
        
        # スキル保持率を計算
        skill_retention = self._calculate_skill_retention(months_gap)
        
        # ペナルティを計算
        penalty = self._calculate_penalty(
            months_gap, career_change, dept_change, skill_retention
        )
        
        # 説明と推奨事項を生成
        explanation = self._generate_explanation(
            months_gap, career_change, dept_change, latest_relevant
        )
        recommendations = self._generate_recommendations(
            months_gap, career_change, dept_change
        )
        
        return ContinuityAssessment(
            has_recent_relevant_experience=(months_gap is not None and months_gap <= 6),
            months_since_relevant_experience=months_gap,
            career_change_detected=career_change,
            department_change_detected=dept_change,
            skill_retention_score=skill_retention,
            penalty_score=penalty,
            explanation=explanation,
            recommendations=recommendations
        )
    
    def _extract_career_timeline(self, resume_text: str) -> List[CareerPeriod]:
        """職歴タイムラインを抽出"""
        timeline = []
        
        # 日付パターンで行を分割
        lines = resume_text.strip().split('\n')
        current_period = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # 日付パターンをチェック
            date_match = re.search(
                r'(\d{4})年?(\d{1,2})?月?\s*[～〜\-–—]\s*(?:(\d{4})年?(\d{1,2})?月?|現在)',
                line
            )
            
            if date_match:
                # 新しい期間の開始
                start_date = self._parse_date(date_match.group(1), date_match.group(2))
                if date_match.group(3):  # 終了日がある場合
                    end_date = self._parse_date(date_match.group(3), date_match.group(4))
                else:  # 現在
                    end_date = None
                
                # 会社名を抽出（より広範囲に）
                company_match = re.search(
                    r'株式会社[ア-ン亜-龥A-Za-z0-9]+|[ア-ン亜-龥A-Za-z0-9]+株式会社|[ア-ン亜-龥A-Za-z0-9]+会社|[ア-ン亜-龥A-Za-z0-9]+ソフトウェア|[ア-ン亜-龥A-Za-z0-9]+システム|[ア-ン亜-龥A-Za-z0-9]+テック',
                    line
                )
                company = company_match.group(0) if company_match else "不明"
                
                # 役職を抽出（より広範囲に）
                role_patterns = [
                    r'エンジニア', r'開発者?', r'プログラマー?', r'SE',
                    r'マネージャー?', r'リーダー?', r'営業', r'企画', r'管理', 
                    r'コンサルタント', r'担当', r'主任', r'係長', r'課長'
                ]
                role = "不明"
                for pattern in role_patterns:
                    match = re.search(pattern, line)
                    if match:
                        role = match.group(0)
                        break
                
                # 部署を抽出
                dept_patterns = [
                    r'開発部', r'営業部', r'企画部', r'管理部', r'システム部',
                    r'技術部', r'設計部', r'製造部', r'[ア-ン亜-龥]+部',
                    r'[ア-ン亜-龥]+チーム', r'[ア-ン亜-龥]+課'
                ]
                department = None
                for pattern in dept_patterns:
                    match = re.search(pattern, line)
                    if match:
                        department = match.group(0)
                        break
                
                current_period = CareerPeriod(
                    role=role,
                    company=company,
                    department=department,
                    start_date=start_date,
                    end_date=end_date,
                    skills=[],
                    is_relevant=False
                )
                timeline.append(current_period)
            
            elif current_period and line.startswith('-'):
                # 職務内容からスキルを抽出
                skills = self._extract_skills(line)
                current_period.skills.extend(skills)
        
        # 重複スキルを除去
        for period in timeline:
            period.skills = list(set(period.skills))
        
        # 時系列順にソート（新しい順）
        timeline.sort(key=lambda x: x.start_date if x.start_date else datetime.min, reverse=True)
        
        return timeline
    
    async def _is_experience_relevant(self,
                                    period: CareerPeriod,
                                    required_skills: List[str],
                                    required_experience: str) -> bool:
        """経験が求めるものと関連しているか判定"""
        
        if self.use_llm and self.skill_matcher:
            # LLMベースの評価
            try:
                # スキルマッチングをバッチで実行
                skill_results = await self.skill_matcher.match_skills_batch(
                    required_skills, 
                    period.skills
                )
                
                # 役職関連性を評価
                # 業務内容の説明を作成（期間のスキルから）
                period_description = f"{period.role}として{'、'.join(period.skills[:5])}等の業務に従事"
                
                role_result = await self.skill_matcher.evaluate_role_relevance(
                    required_experience,
                    period.role,
                    period_description
                )
                
                # マッチしたスキルをカウント
                skill_match_count = sum(1 for result in skill_results if result.is_match)
                skill_match_ratio = skill_match_count / len(required_skills) if required_skills else 0
                
                # 詳細なデバッグ情報
                print(f"    期間判定: {period.role} at {period.company}")
                print(f"      LLMスキル評価:")
                for result in skill_results[:3]:  # 最初の3つを表示
                    if result.is_match:
                        print(f"        ✓ {result.required_skill} ≈ {result.matched_candidate_skill} (スコア: {result.match_score:.2f})")
                        print(f"          理由: {result.reasoning}")
                
                print(f"      スキル一致: {skill_match_count}/{len(required_skills)} ({skill_match_ratio:.1%})")
                print(f"      役職関連性: {role_result.is_relevant} (スコア: {role_result.relevance_score:.2f})")
                if role_result.matched_aspects:
                    print(f"        一致要素: {', '.join(role_result.matched_aspects)}")
                print(f"        理由: {role_result.reasoning}")
                
                # 総合判定（スキルマッチ30%以上または役職関連性60%以上）
                is_relevant = skill_match_ratio >= 0.3 or role_result.relevance_score >= 0.6
                print(f"      → 関連性: {'あり' if is_relevant else 'なし'}")
                
                return is_relevant
                
            except Exception as e:
                print(f"      LLM評価エラー: {e}")
                print(f"      従来の評価方法にフォールバック")
                # エラー時は従来の方法にフォールバック
                return self._is_experience_relevant_legacy(
                    period, required_skills, required_experience
                )
        else:
            # 従来の評価方法
            return self._is_experience_relevant_legacy(
                period, required_skills, required_experience
            )
    
    def _is_experience_relevant_legacy(self,
                                     period: CareerPeriod,
                                     required_skills: List[str],
                                     required_experience: str) -> bool:
        """従来の方法で経験が求めるものと関連しているか判定"""
        # スキルの一致度をチェック
        skill_match_count = 0
        for req_skill in required_skills:
            for period_skill in period.skills:
                if req_skill.lower() in period_skill.lower() or period_skill.lower() in req_skill.lower():
                    skill_match_count += 1
                    break
        
        skill_match_ratio = skill_match_count / len(required_skills) if required_skills else 0
        
        # 役職の一致度をチェック
        role_keywords = self._extract_role_keywords(required_experience)
        role_relevant = any(
            keyword in period.role.lower()
            for keyword in role_keywords
        )
        
        # デバッグ情報
        print(f"    期間判定: {period.role} at {period.company}")
        print(f"      スキル一致: {skill_match_count}/{len(required_skills)} ({skill_match_ratio:.1%})")
        print(f"      期間スキル: {period.skills}")
        print(f"      必須スキル: {required_skills}")
        print(f"      役職関連性: {role_relevant} (キーワード: {role_keywords})")
        
        # 30%以上のスキル一致または役職一致で関連ありと判定
        is_relevant = skill_match_ratio >= 0.3 or role_relevant
        print(f"      → 関連性: {'あり' if is_relevant else 'なし'}")
        
        return is_relevant
    
    def _find_latest_relevant_experience(self,
                                       timeline: List[CareerPeriod]) -> Optional[CareerPeriod]:
        """最新の関連経験を特定"""
        for period in timeline:
            if period.is_relevant:
                return period
        return None
    
    def _detect_career_change(self, resume_text: str, timeline: List[CareerPeriod]) -> bool:
        """キャリアチェンジを検出"""
        # キーワードで検出
        for indicator in self.career_change_indicators:
            if indicator in resume_text:
                return True
        
        # 直近の職歴で大きな変化があるか
        if len(timeline) >= 2:
            current = timeline[0]
            previous = timeline[1]
            
            # 異なる業界への移動を検出
            if self._are_different_industries(current.company, previous.company):
                return True
            
            # 役職の大幅な変化を検出
            if self._are_different_roles(current.role, previous.role):
                return True
        
        return False
    
    def _detect_department_change(self, resume_text: str, timeline: List[CareerPeriod]) -> bool:
        """部署異動を検出"""
        # キーワードで検出
        for indicator in self.department_change_indicators:
            if indicator in resume_text:
                return True
        
        # 同一会社内での部署変更を検出
        if len(timeline) >= 2:
            for i in range(len(timeline) - 1):
                current = timeline[i]
                next_period = timeline[i + 1]
                
                # 同じ会社で部署が異なる
                if (current.company == next_period.company and
                    current.department and next_period.department and
                    current.department != next_period.department):
                    return True
        
        return False
    
    def _calculate_experience_gap(self, latest_relevant: Optional[CareerPeriod]) -> Optional[int]:
        """関連経験からのブランク期間を計算（月単位）"""
        if not latest_relevant:
            return None
        
        # 現在の職であればブランクなし
        if latest_relevant.end_date is None:
            return 0
        
        # 終了日から現在までの月数を計算
        months_diff = (datetime.now() - latest_relevant.end_date).days / 30
        return int(months_diff)
    
    def _calculate_skill_retention(self, months_gap: Optional[int]) -> float:
        """スキル保持率を計算"""
        if months_gap is None:
            return 0.5  # 関連経験がない場合
        
        # 指数的減衰モデル
        retention = (1 - self.skill_decay_rate) ** months_gap
        return max(0.3, retention)  # 最低30%は保持
    
    def _calculate_penalty(self,
                         months_gap: Optional[int],
                         career_change: bool,
                         dept_change: bool,
                         skill_retention: float) -> float:
        """ペナルティを計算"""
        penalty = 0.0
        
        # ブランク期間によるペナルティ
        if months_gap is None:
            penalty = 0.5  # 関連経験がない
        elif months_gap <= 0:
            penalty = self.penalty_thresholds["no_gap"]
        elif months_gap <= 6:
            penalty = self.penalty_thresholds["short_gap"]
        elif months_gap <= 12:
            penalty = self.penalty_thresholds["medium_gap"]
        elif months_gap <= 24:
            penalty = self.penalty_thresholds["long_gap"]
        else:
            penalty = self.penalty_thresholds["very_long_gap"]
        
        # キャリアチェンジによる追加ペナルティ
        if career_change:
            penalty += 0.15
        
        # 部署異動による追加ペナルティ（軽度）
        if dept_change and not career_change:
            penalty += 0.05
        
        # スキル保持率による調整
        penalty *= (2 - skill_retention)  # スキル保持率が低いほどペナルティ増
        
        return min(penalty, 0.5)  # 最大50%減点
    
    def _generate_explanation(self,
                            months_gap: Optional[int],
                            career_change: bool,
                            dept_change: bool,
                            latest_relevant: Optional[CareerPeriod]) -> str:
        """説明文を生成"""
        explanations = []
        
        if months_gap is None:
            explanations.append("求める経験に関連する職歴が確認できませんでした。")
        elif months_gap == 0:
            explanations.append("現在も関連する業務に従事しています。")
        elif months_gap <= 6:
            explanations.append(f"関連経験から{months_gap}ヶ月のブランクがあります。")
        elif months_gap <= 12:
            explanations.append(f"関連経験から{months_gap}ヶ月経過しており、スキルの陳腐化が懸念されます。")
        else:
            explanations.append(f"関連経験から{months_gap}ヶ月（{months_gap//12}年{months_gap%12}ヶ月）経過しています。")
        
        if career_change:
            explanations.append("キャリアチェンジが確認されました。")
        
        if dept_change:
            explanations.append("部署異動による業務内容の変化がありました。")
        
        if latest_relevant:
            explanations.append(f"最後の関連経験: {latest_relevant.company} {latest_relevant.role}")
        
        return " ".join(explanations)
    
    def _generate_recommendations(self,
                                months_gap: Optional[int],
                                career_change: bool,
                                dept_change: bool) -> List[str]:
        """推奨事項を生成"""
        recommendations = []
        
        if months_gap is not None and months_gap > 6:
            recommendations.append("スキルの現在レベルを面接で確認することを推奨")
            recommendations.append("最新の技術トレンドへの理解度を確認")
        
        if career_change:
            recommendations.append("キャリアチェンジの動機と意欲を確認")
            recommendations.append("過去の経験を新しい役割でどう活かせるか確認")
        
        if dept_change:
            recommendations.append("異動後の適応状況を確認")
        
        if months_gap is None:
            recommendations.append("関連する経験の有無を詳細に確認")
            recommendations.append("ポテンシャルと学習能力を重点的に評価")
        
        return recommendations
    
    def _parse_date(self, year: str, month: Optional[str]) -> datetime:
        """日付をパース"""
        try:
            y = int(year)
            m = int(month) if month else 1
            return datetime(y, m, 1)
        except:
            return datetime.now()
    
    def _extract_skills(self, text: str) -> List[str]:
        """スキルを抽出"""
        skills = []
        
        # 技術スキル
        tech_pattern = r'\b(Python|Java|JavaScript|TypeScript|Go|Ruby|PHP|C\+\+|C#|Swift|React|Vue|Angular|Django|Flask|Spring|Rails|Laravel|AWS|Azure|GCP|Docker|Kubernetes)\b'
        skills.extend(re.findall(tech_pattern, text, re.IGNORECASE))
        
        # ビジネススキル
        business_skills = ["マネジメント", "リーダーシップ", "プロジェクト管理", "営業", "マーケティング"]
        for skill in business_skills:
            if skill in text:
                skills.append(skill)
        
        return list(set(skills))
    
    def _extract_role_keywords(self, required_experience: str) -> List[str]:
        """求める経験から役職キーワードを抽出"""
        keywords = []
        
        role_patterns = [
            "エンジニア", "開発", "設計", "実装", "プログラミング",
            "マネージャー", "リーダー", "管理", "マネジメント",
            "営業", "セールス", "コンサル", "企画", "戦略"
        ]
        
        for pattern in role_patterns:
            if pattern in required_experience:
                keywords.append(pattern.lower())
        
        return keywords
    
    def _are_different_industries(self, company1: str, company2: str) -> bool:
        """異なる業界か判定"""
        # 簡易的な業界判定
        it_keywords = ["システム", "ソフトウェア", "IT", "テクノロジー"]
        finance_keywords = ["銀行", "証券", "保険", "金融"]
        manufacturing_keywords = ["製造", "メーカー", "工業", "製作"]
        
        industry1 = None
        industry2 = None
        
        # 会社1の業界を判定
        for keyword in it_keywords:
            if keyword in company1:
                industry1 = "IT"
                break
        for keyword in finance_keywords:
            if keyword in company1:
                industry1 = "Finance"
                break
        for keyword in manufacturing_keywords:
            if keyword in company1:
                industry1 = "Manufacturing"
                break
        
        # 会社2の業界を判定
        for keyword in it_keywords:
            if keyword in company2:
                industry2 = "IT"
                break
        for keyword in finance_keywords:
            if keyword in company2:
                industry2 = "Finance"
                break
        for keyword in manufacturing_keywords:
            if keyword in company2:
                industry2 = "Manufacturing"
                break
        
        return industry1 != industry2 and industry1 is not None and industry2 is not None
    
    def _are_different_roles(self, role1: str, role2: str) -> bool:
        """異なる役職か判定"""
        # 技術系とビジネス系の分類
        technical_roles = ["エンジニア", "開発", "プログラマ", "設計"]
        business_roles = ["営業", "マーケティング", "企画", "コンサル"]
        management_roles = ["マネージャー", "リーダー", "管理", "ディレクター"]
        
        type1 = None
        type2 = None
        
        # 役職タイプを判定
        for role in technical_roles:
            if role in role1:
                type1 = "technical"
                break
        for role in business_roles:
            if role in role1:
                type1 = "business"
                break
        for role in management_roles:
            if role in role1:
                type1 = "management"
                break
        
        for role in technical_roles:
            if role in role2:
                type2 = "technical"
                break
        for role in business_roles:
            if role in role2:
                type2 = "business"
                break
        for role in management_roles:
            if role in role2:
                type2 = "management"
                break
        
        return type1 != type2 and type1 is not None and type2 is not None
    
    def format_continuity_report(self, assessment: ContinuityAssessment) -> str:
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
        
        # 説明
        lines.append("\n## 評価")
        lines.append(assessment.explanation)
        
        # 推奨事項
        if assessment.recommendations:
            lines.append("\n## 推奨事項")
            for rec in assessment.recommendations:
                lines.append(f"- {rec}")
        
        return '\n'.join(lines)