"""
動的重み付けシステム
求人の特性に応じて評価項目の重みを動的に調整
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import re


@dataclass
class WeightProfile:
    """重み付けプロファイル"""
    required_skills: float = 0.45  # 必須要件
    practical_ability: float = 0.25  # 実務遂行能力
    preferred_skills: float = 0.15  # 歓迎要件
    organizational_fit: float = 0.10  # 組織適合性
    outstanding_career: float = 0.05  # 突出した経歴
    
    def normalize(self):
        """重みを正規化（合計が1.0になるように）"""
        total = (self.required_skills + self.practical_ability + 
                self.preferred_skills + self.organizational_fit + 
                self.outstanding_career)
        if total > 0:
            self.required_skills /= total
            self.practical_ability /= total
            self.preferred_skills /= total
            self.organizational_fit /= total
            self.outstanding_career /= total


class DynamicWeightAdjuster:
    """動的重み付け調整器"""
    
    def __init__(self):
        # 業界別の重みプロファイル
        self.industry_profiles = {
            "IT・テクノロジー": WeightProfile(
                required_skills=0.50,  # 技術要件重視
                practical_ability=0.25,
                preferred_skills=0.15,
                organizational_fit=0.05,
                outstanding_career=0.05
            ),
            "金融・銀行": WeightProfile(
                required_skills=0.40,
                practical_ability=0.20,
                preferred_skills=0.10,
                organizational_fit=0.25,  # 組織適合性重視
                outstanding_career=0.05
            ),
            "スタートアップ": WeightProfile(
                required_skills=0.35,
                practical_ability=0.30,  # 実務能力重視
                preferred_skills=0.10,
                organizational_fit=0.15,
                outstanding_career=0.10  # ユニークな経歴も評価
            ),
            "製造業": WeightProfile(
                required_skills=0.45,
                practical_ability=0.30,
                preferred_skills=0.10,
                organizational_fit=0.10,
                outstanding_career=0.05
            ),
            "コンサルティング": WeightProfile(
                required_skills=0.40,
                practical_ability=0.25,
                preferred_skills=0.15,
                organizational_fit=0.10,
                outstanding_career=0.10
            )
        }
        
        # 職種別の調整係数
        self.role_adjustments = {
            "エンジニア": {
                "required_skills": 1.2,  # 技術要件を強化
                "organizational_fit": 0.8
            },
            "マネージャー": {
                "practical_ability": 1.2,  # 実務能力を強化
                "organizational_fit": 1.1
            },
            "経営幹部": {
                "organizational_fit": 1.3,  # 組織適合性を強化
                "outstanding_career": 1.5  # 突出した経歴を重視
            },
            "営業": {
                "practical_ability": 1.2,
                "preferred_skills": 0.9
            },
            "企画": {
                "required_skills": 0.9,
                "practical_ability": 1.1,
                "outstanding_career": 1.2
            }
        }
        
        # キーワードベースの調整
        self.keyword_adjustments = {
            "即戦力": {
                "practical_ability": 1.3,
                "required_skills": 1.1
            },
            "ポテンシャル": {
                "organizational_fit": 1.2,
                "preferred_skills": 1.1,
                "required_skills": 0.9
            },
            "リーダーシップ": {
                "practical_ability": 1.2,
                "outstanding_career": 1.2
            },
            "専門性": {
                "required_skills": 1.3,
                "practical_ability": 1.1
            },
            "チームワーク": {
                "organizational_fit": 1.3,
                "practical_ability": 0.9
            },
            "イノベーション": {
                "outstanding_career": 1.4,
                "preferred_skills": 1.2
            }
        }
    
    def adjust_weights(self, job_data: Dict, structured_data: Optional[Dict] = None) -> WeightProfile:
        """求人データに基づいて重みを調整"""
        # デフォルトプロファイルから開始
        profile = WeightProfile()
        
        # 1. 業界に基づく基本プロファイルを適用
        industry = self._extract_industry(job_data, structured_data)
        if industry:
            for key, base_profile in self.industry_profiles.items():
                if key in industry:
                    profile = self._copy_profile(base_profile)
                    print(f"  [WeightAdjuster] 業界プロファイル適用: {key}")
                    break
        
        # 2. 職種に基づく調整
        role = self._extract_role(job_data, structured_data)
        if role:
            adjustments = self._get_role_adjustments(role)
            if adjustments:
                profile = self._apply_adjustments(profile, adjustments)
                print(f"  [WeightAdjuster] 職種調整適用: {role}")
        
        # 3. キーワードに基づく調整
        keywords = self._extract_keywords(job_data, structured_data)
        for keyword, adjustments in self.keyword_adjustments.items():
            if keyword in keywords:
                profile = self._apply_adjustments(profile, adjustments)
                print(f"  [WeightAdjuster] キーワード調整適用: {keyword}")
        
        # 4. 経験年数要件に基づく調整
        experience_years = self._extract_experience_years(job_data, structured_data)
        if experience_years:
            profile = self._adjust_by_experience(profile, experience_years)
        
        # 5. 給与レンジに基づく調整
        salary_range = self._extract_salary_range(job_data, structured_data)
        if salary_range:
            profile = self._adjust_by_salary(profile, salary_range)
        
        # 正規化
        profile.normalize()
        
        return profile
    
    def _extract_industry(self, job_data: Dict, structured_data: Optional[Dict]) -> str:
        """業界情報を抽出"""
        # 構造化データから
        if structured_data and structured_data.get('basic_info', {}).get('industry'):
            industry = structured_data['basic_info']['industry']
            print(f"    [WeightAdjuster] 構造化データから業界を取得: {industry}")
            return industry
        
        # job_descriptionから抽出
        text = job_data.get('job_description', '') + ' ' + job_data.get('title', '')
        
        # より具体的な業界キーワードを優先的にチェック（順序を変更）
        industries = {
            "金融・銀行": ["金融", "銀行", "証券", "保険", "ファイナンス", "投資", "資産運用"],
            "製造業": ["製造", "メーカー", "工場", "生産", "品質管理", "製品開発", "量産"],
            "コンサルティング": ["コンサル", "戦略立案", "アドバイザリー", "経営支援", "業務改善"],
            "スタートアップ": ["スタートアップ", "ベンチャー", "創業", "急成長", "新規事業"],
            "小売・流通": ["小売", "流通", "販売", "店舗", "EC", "リテール"],
            "医療・ヘルスケア": ["医療", "病院", "クリニック", "製薬", "ヘルスケア", "医薬品"],
            "不動産": ["不動産", "建設", "ゼネコン", "デベロッパー", "賃貸", "売買"],
            "IT・テクノロジー": ["ソフトウェア開発", "プログラミング", "エンジニア", "IT企業", "テック企業", "SaaS", "AI", "機械学習"]
        }
        
        # デバッグ: どのキーワードがマッチしたか記録
        matched_industries = []
        for industry, keywords in industries.items():
            matched_keywords = [kw for kw in keywords if kw in text]
            if matched_keywords:
                matched_industries.append((industry, matched_keywords))
                print(f"    [WeightAdjuster] {industry}のキーワードがマッチ: {matched_keywords}")
        
        # 最も多くのキーワードがマッチした業界を選択
        if matched_industries:
            best_match = max(matched_industries, key=lambda x: len(x[1]))
            print(f"    [WeightAdjuster] 最終的に選択された業界: {best_match[0]}")
            return best_match[0]
        
        print(f"    [WeightAdjuster] 業界を特定できませんでした")
        return ""
    
    def _extract_role(self, job_data: Dict, structured_data: Optional[Dict]) -> str:
        """職種情報を抽出"""
        title = job_data.get('title', '')
        
        # 職種キーワードをチェック
        roles = {
            "エンジニア": ["エンジニア", "開発", "プログラマ", "Developer"],
            "マネージャー": ["マネージャー", "管理", "リーダー", "課長", "部長"],
            "経営幹部": ["執行役員", "取締役", "CTO", "CFO", "COO", "経営"],
            "営業": ["営業", "セールス", "Sales", "アカウント"],
            "企画": ["企画", "プランナー", "ストラテジスト", "マーケティング"]
        }
        
        for role, keywords in roles.items():
            if any(kw in title for kw in keywords):
                return role
        
        return ""
    
    def _extract_keywords(self, job_data: Dict, structured_data: Optional[Dict]) -> str:
        """重要キーワードを抽出"""
        text = (job_data.get('job_description', '') + ' ' + 
                job_data.get('memo', '') + ' ' + 
                job_data.get('title', ''))
        
        return text.lower()
    
    def _extract_experience_years(self, job_data: Dict, structured_data: Optional[Dict]) -> Optional[int]:
        """必要経験年数を抽出"""
        if structured_data and structured_data.get('experience_years_min'):
            return structured_data['experience_years_min']
        
        # テキストから抽出
        text = job_data.get('job_description', '')
        match = re.search(r'(\d+)年以上', text)
        if match:
            return int(match.group(1))
        
        return None
    
    def _extract_salary_range(self, job_data: Dict, structured_data: Optional[Dict]) -> Optional[Tuple[int, int]]:
        """給与レンジを抽出"""
        if structured_data:
            min_salary = structured_data.get('salary_min')
            max_salary = structured_data.get('salary_max')
            if min_salary and max_salary:
                return (min_salary, max_salary)
        
        return None
    
    def _get_role_adjustments(self, role: str) -> Dict[str, float]:
        """職種に基づく調整係数を取得"""
        for key, adjustments in self.role_adjustments.items():
            if key in role:
                return adjustments
        return {}
    
    def _apply_adjustments(self, profile: WeightProfile, adjustments: Dict[str, float]) -> WeightProfile:
        """調整係数を適用"""
        new_profile = self._copy_profile(profile)
        
        for attr, factor in adjustments.items():
            if hasattr(new_profile, attr):
                current_value = getattr(new_profile, attr)
                setattr(new_profile, attr, current_value * factor)
        
        return new_profile
    
    def _adjust_by_experience(self, profile: WeightProfile, years: int) -> WeightProfile:
        """経験年数に基づく調整"""
        if years >= 10:
            # シニアポジション：実績と組織適合性を重視
            profile.practical_ability *= 1.2
            profile.organizational_fit *= 1.2
            profile.outstanding_career *= 1.3
        elif years >= 5:
            # ミドルポジション：バランス型
            profile.required_skills *= 1.1
            profile.practical_ability *= 1.1
        else:
            # ジュニアポジション：基礎スキル重視
            profile.required_skills *= 1.2
            profile.preferred_skills *= 1.1
        
        return profile
    
    def _adjust_by_salary(self, profile: WeightProfile, salary_range: Tuple[int, int]) -> WeightProfile:
        """給与レンジに基づく調整"""
        max_salary = salary_range[1]
        
        if max_salary >= 10000000:  # 1000万円以上
            # ハイクラス：全体的に要求水準が高い
            profile.required_skills *= 1.1
            profile.practical_ability *= 1.2
            profile.organizational_fit *= 1.2
            profile.outstanding_career *= 1.3
        elif max_salary >= 7000000:  # 700万円以上
            # ミドルクラス：実務能力重視
            profile.practical_ability *= 1.15
            profile.required_skills *= 1.05
        
        return profile
    
    def _copy_profile(self, profile: WeightProfile) -> WeightProfile:
        """プロファイルをコピー"""
        return WeightProfile(
            required_skills=profile.required_skills,
            practical_ability=profile.practical_ability,
            preferred_skills=profile.preferred_skills,
            organizational_fit=profile.organizational_fit,
            outstanding_career=profile.outstanding_career
        )
    
    def get_weight_explanation(self, profile: WeightProfile) -> str:
        """重み付けの説明を生成"""
        explanations = []
        
        # 最も重視される項目を特定
        weights = {
            "必須要件": profile.required_skills,
            "実務遂行能力": profile.practical_ability,
            "歓迎要件": profile.preferred_skills,
            "組織適合性": profile.organizational_fit,
            "突出した経歴": profile.outstanding_career
        }
        
        sorted_weights = sorted(weights.items(), key=lambda x: x[1], reverse=True)
        
        explanations.append(f"最重視項目: {sorted_weights[0][0]} ({sorted_weights[0][1]:.0%})")
        explanations.append(f"次点: {sorted_weights[1][0]} ({sorted_weights[1][1]:.0%})")
        
        # 特徴的な重み付けを説明
        if profile.required_skills > 0.5:
            explanations.append("技術要件を特に重視する評価")
        if profile.organizational_fit > 0.15:
            explanations.append("企業文化との適合性を重視")
        if profile.outstanding_career > 0.1:
            explanations.append("ユニークな経歴を高く評価")
        
        return " / ".join(explanations)