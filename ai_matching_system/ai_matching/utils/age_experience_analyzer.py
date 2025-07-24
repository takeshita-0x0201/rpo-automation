"""
年齢と経験社数の適合性評価
転職回数が年齢に対して適切かどうかを分析
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import re


@dataclass
class AgeExperienceAssessment:
    """年齢・経験社数評価"""
    candidate_age: Optional[int]
    total_companies: int
    career_years: Optional[int]  # 推定キャリア年数
    average_tenure: Optional[float]  # 平均在籍年数
    job_change_frequency: str  # "適切", "やや多い", "多すぎる", "少なすぎる"
    stability_score: float  # 0.0-1.0 (安定性スコア)
    adjustment_factor: float  # 0.5-1.2 (評価調整係数)
    explanation: str
    recommendations: List[str]
    risk_factors: List[str]


class AgeExperienceAnalyzer:
    """年齢・経験社数分析器"""
    
    def __init__(self):
        # 年齢別の適切な転職回数の基準
        self.optimal_job_changes = {
            20: {"min": 0, "max": 2, "optimal": 1},  # 20代
            25: {"min": 0, "max": 3, "optimal": 2},
            30: {"min": 1, "max": 4, "optimal": 3},  # 30代
            35: {"min": 2, "max": 5, "optimal": 3},
            40: {"min": 2, "max": 6, "optimal": 4},  # 40代
            45: {"min": 3, "max": 6, "optimal": 4},
            50: {"min": 3, "max": 7, "optimal": 5},  # 50代以上
        }
        
        # 平均在籍年数の評価基準
        self.tenure_standards = {
            "excellent": 4.0,    # 4年以上: 非常に安定
            "good": 3.0,         # 3-4年: 良好
            "acceptable": 2.0,   # 2-3年: 許容範囲
            "concerning": 1.5,   # 1.5-2年: 懸念
            "problematic": 1.0   # 1年未満: 問題
        }
        
        # 調整係数の設定
        self.adjustment_factors = {
            "excellent": 1.2,     # 20%ボーナス
            "good": 1.1,          # 10%ボーナス
            "acceptable": 1.0,    # 変更なし
            "concerning": 0.9,    # 10%減点
            "problematic": 0.7,   # 30%減点
            "very_problematic": 0.5  # 50%減点
        }
    
    def analyze_age_experience_fit(self,
                                 candidate_age: Optional[int],
                                 total_companies: int,
                                 resume_text: str = "",
                                 current_position_years: Optional[float] = None) -> AgeExperienceAssessment:
        """年齢と経験社数の適合性を分析"""
        
        # 年齢を整数に変換（文字列で渡された場合の対応）
        if candidate_age is not None:
            try:
                candidate_age = int(candidate_age) if isinstance(candidate_age, str) else candidate_age
            except (ValueError, TypeError):
                candidate_age = None
        
        # 経験社数を整数に変換（文字列で渡された場合の対応）
        try:
            total_companies = int(total_companies) if isinstance(total_companies, str) else total_companies
        except (ValueError, TypeError):
            total_companies = 1  # デフォルト値として1社を設定
        
        # キャリア年数を推定
        career_years = self._estimate_career_years(candidate_age, resume_text)
        
        # 平均在籍年数を計算
        average_tenure = self._calculate_average_tenure(
            career_years, total_companies, current_position_years
        )
        
        # 転職頻度を評価
        job_change_frequency = self._evaluate_job_change_frequency(
            candidate_age, total_companies
        )
        
        # 安定性スコアを計算
        stability_score = self._calculate_stability_score(
            candidate_age, total_companies, average_tenure
        )
        
        # 調整係数を決定
        adjustment_factor = self._determine_adjustment_factor(
            job_change_frequency, stability_score, average_tenure
        )
        
        # 説明文を生成
        explanation = self._generate_explanation(
            candidate_age, total_companies, career_years, 
            average_tenure, job_change_frequency
        )
        
        # 推奨事項を生成
        recommendations = self._generate_recommendations(
            job_change_frequency, stability_score, average_tenure
        )
        
        # リスク要因を特定
        risk_factors = self._identify_risk_factors(
            candidate_age, total_companies, average_tenure
        )
        
        return AgeExperienceAssessment(
            candidate_age=candidate_age,
            total_companies=total_companies,
            career_years=career_years,
            average_tenure=average_tenure,
            job_change_frequency=job_change_frequency,
            stability_score=stability_score,
            adjustment_factor=adjustment_factor,
            explanation=explanation,
            recommendations=recommendations,
            risk_factors=risk_factors
        )
    
    def _estimate_career_years(self, age: Optional[int], resume_text: str) -> Optional[int]:
        """キャリア年数を推定"""
        if not age:
            return None
        
        # 年齢を整数に変換（文字列で渡された場合の対応）
        try:
            age = int(age) if isinstance(age, str) else age
        except (ValueError, TypeError):
            return None
        
        # 一般的な就職年齢から推定
        standard_career_start = 22  # 大卒想定
        
        # レジュメから最初の就職年を抽出を試行
        first_job_year = self._extract_first_job_year(resume_text)
        if first_job_year:
            current_year = 2024  # 現在年
            career_years = current_year - first_job_year
            return max(0, career_years)
        
        # 年齢から推定
        estimated_years = max(0, age - standard_career_start)
        return estimated_years
    
    def _extract_first_job_year(self, resume_text: str) -> Optional[int]:
        """レジュメから最初の就職年を抽出"""
        # 年月パターンを全て抽出
        date_patterns = re.findall(
            r'(\d{4})年?(\d{1,2})?月?\s*[～〜\-–—]',
            resume_text
        )
        
        if date_patterns:
            # 最も古い年を取得
            years = [int(year) for year, _ in date_patterns if year.isdigit()]
            if years:
                return min(years)
        
        return None
    
    def _calculate_average_tenure(self,
                                career_years: Optional[int],
                                total_companies: int,
                                current_position_years: Optional[float]) -> Optional[float]:
        """平均在籍年数を計算"""
        if not career_years or total_companies <= 0:
            return None
        
        if total_companies == 1:
            # 1社のみの場合は現在の在籍年数または推定年数
            return current_position_years or career_years
        
        # 複数社の場合
        # 現在の会社を除いた過去の平均在籍年数 + 現在の在籍年数
        past_companies = total_companies - 1
        if past_companies > 0:
            current_years = current_position_years or 2.0  # デフォルト2年
            remaining_years = max(0, career_years - current_years)
            past_average = remaining_years / past_companies if past_companies > 0 else 0
            
            # 全体の平均を計算
            total_years = remaining_years + current_years
            return total_years / total_companies
        
        return career_years / total_companies
    
    def _evaluate_job_change_frequency(self,
                                     age: Optional[int],
                                     total_companies: int) -> str:
        """転職頻度を評価"""
        if not age:
            return "判定不可"
        
        # 年齢を整数に変換（文字列で渡された場合の対応）
        try:
            age = int(age) if isinstance(age, str) else age
        except (ValueError, TypeError):
            return "判定不可"
        
        # 経験社数を整数に変換（文字列で渡された場合の対応）
        try:
            total_companies = int(total_companies) if isinstance(total_companies, str) else total_companies
        except (ValueError, TypeError):
            total_companies = 1  # デフォルト値として1社を設定
        
        # 年齢に基づく基準を取得
        standards = self._get_age_standards(age)
        job_changes = total_companies - 1  # 転職回数
        
        if job_changes <= standards["min"]:
            return "少なすぎる"
        elif job_changes <= standards["optimal"]:
            return "適切"
        elif job_changes <= standards["max"]:
            return "やや多い"
        else:
            return "多すぎる"
    
    def _get_age_standards(self, age: int) -> Dict[str, int]:
        """年齢に応じた基準を取得"""
        # 最も近い年齢基準を選択
        closest_age = min(self.optimal_job_changes.keys(), 
                         key=lambda x: abs(x - age))
        return self.optimal_job_changes[closest_age]
    
    def _calculate_stability_score(self,
                                 age: Optional[int],
                                 total_companies: int,
                                 average_tenure: Optional[float]) -> float:
        """安定性スコアを計算"""
        score = 1.0
        
        # 年齢を整数に変換（文字列で渡された場合の対応）
        if age:
            try:
                age = int(age) if isinstance(age, str) else age
            except (ValueError, TypeError):
                age = None
        
        # 経験社数を整数に変換（文字列で渡された場合の対応）
        try:
            total_companies = int(total_companies) if isinstance(total_companies, str) else total_companies
        except (ValueError, TypeError):
            total_companies = 1  # デフォルト値として1社を設定
            
        # 転職頻度による調整
        if age:
            frequency = self._evaluate_job_change_frequency(age, total_companies)
            frequency_adjustments = {
                "適切": 0.0,
                "やや多い": -0.1,
                "多すぎる": -0.3,
                "少なすぎる": -0.05  # 経験不足のリスク
            }
            score += frequency_adjustments.get(frequency, 0)
        
        # 平均在籍年数による調整
        if average_tenure:
            if average_tenure >= self.tenure_standards["excellent"]:
                score += 0.2
            elif average_tenure >= self.tenure_standards["good"]:
                score += 0.1
            elif average_tenure >= self.tenure_standards["acceptable"]:
                score += 0.0
            elif average_tenure >= self.tenure_standards["concerning"]:
                score -= 0.1
            else:
                score -= 0.2
        
        return max(0.0, min(1.0, score))
    
    def _determine_adjustment_factor(self,
                                   frequency: str,
                                   stability_score: float,
                                   average_tenure: Optional[float]) -> float:
        """評価調整係数を決定"""
        # 基本係数
        base_factor = 1.0
        
        # 転職頻度による調整
        frequency_factors = {
            "適切": 1.0,
            "やや多い": 0.95,
            "多すぎる": 0.8,
            "少なすぎる": 0.9
        }
        base_factor *= frequency_factors.get(frequency, 1.0)
        
        # 安定性スコアによる調整
        if stability_score >= 0.8:
            base_factor *= 1.1  # 高安定性ボーナス
        elif stability_score <= 0.4:
            base_factor *= 0.9  # 低安定性ペナルティ
        
        # 平均在籍年数による追加調整
        if average_tenure:
            if average_tenure < 1.0:
                base_factor *= 0.85  # 短期離職リスク
            elif average_tenure > 5.0:
                base_factor *= 1.05  # 長期安定ボーナス
        
        return max(0.5, min(1.2, base_factor))
    
    def _generate_explanation(self,
                            age: Optional[int],
                            total_companies: int,
                            career_years: Optional[int],
                            average_tenure: Optional[float],
                            frequency: str) -> str:
        """説明文を生成"""
        explanations = []
        
        if age:
            explanations.append(f"{age}歳で{total_companies}社経験")
        else:
            explanations.append(f"{total_companies}社経験")
        
        if career_years:
            explanations.append(f"推定キャリア年数: {career_years}年")
        
        if average_tenure:
            explanations.append(f"平均在籍年数: {average_tenure:.1f}年")
        
        # 転職頻度の評価
        frequency_messages = {
            "適切": "転職頻度は適切な範囲内です",
            "やや多い": "転職頻度がやや多めですが許容範囲内です",
            "多すぎる": "転職頻度が多すぎる可能性があります",
            "少なすぎる": "転職経験が少なく、多様性に欠ける可能性があります"
        }
        explanations.append(frequency_messages.get(frequency, "転職頻度の判定ができません"))
        
        return "。".join(explanations) + "。"
    
    def _generate_recommendations(self,
                                frequency: str,
                                stability_score: float,
                                average_tenure: Optional[float]) -> List[str]:
        """推奨事項を生成"""
        recommendations = []
        
        # 転職頻度別の推奨
        if frequency == "多すぎる":
            recommendations.extend([
                "転職理由と動機を詳細に確認することを推奨",
                "定着意欲と長期的なキャリアプランを確認",
                "過去の離職理由に一貫性があるかチェック"
            ])
        elif frequency == "やや多い":
            recommendations.extend([
                "転職理由の妥当性を確認",
                "今回の転職で長期定着する意向を確認"
            ])
        elif frequency == "少なすぎる":
            recommendations.extend([
                "多様な環境への適応力を面接で確認",
                "新しい挑戦への意欲と学習能力を評価"
            ])
        
        # 安定性スコア別の推奨
        if stability_score < 0.5:
            recommendations.append("定着性に関するリスクを慎重に評価")
        
        # 平均在籍年数別の推奨
        if average_tenure and average_tenure < 2.0:
            recommendations.extend([
                "短期離職のリスクを面接で確認",
                "コミット期間に関する明確な合意を形成"
            ])
        
        return recommendations
    
    def _identify_risk_factors(self,
                             age: Optional[int],
                             total_companies: int,
                             average_tenure: Optional[float]) -> List[str]:
        """リスク要因を特定"""
        risks = []
        
        # 年齢を整数に変換（文字列で渡された場合の対応）
        if age:
            try:
                age = int(age) if isinstance(age, str) else age
            except (ValueError, TypeError):
                age = None
        
        # 経験社数を整数に変換（文字列で渡された場合の対応）
        try:
            total_companies = int(total_companies) if isinstance(total_companies, str) else total_companies
        except (ValueError, TypeError):
            total_companies = 1  # デフォルト値として1社を設定
        
        # 高頻度転職リスク
        if age and total_companies > 0:
            job_changes = total_companies - 1
            if age < 30 and job_changes >= 4:
                risks.append("20代で転職回数が多い")
            elif age < 40 and job_changes >= 6:
                risks.append("30代で転職回数が過多")
            elif job_changes >= 8:
                risks.append("転職回数が非常に多い")
        
        # 短期離職リスク
        if average_tenure:
            if average_tenure < 1.0:
                risks.append("平均在籍期間が1年未満")
            elif average_tenure < 1.5:
                risks.append("短期離職の傾向")
        
        # 経験不足リスク  
        if total_companies == 1 and age and age > 35:
            risks.append("転職経験不足による適応力の懸念")
        
        return risks
    
    def format_assessment_report(self, assessment: AgeExperienceAssessment) -> str:
        """評価レポートをフォーマット"""
        lines = []
        lines.append("# 年齢・経験社数適合性評価")
        
        # サマリー
        lines.append("\n## サマリー")
        if assessment.candidate_age:
            lines.append(f"- 年齢: {assessment.candidate_age}歳")
        lines.append(f"- 経験社数: {assessment.total_companies}社")
        if assessment.career_years:
            lines.append(f"- 推定キャリア年数: {assessment.career_years}年")
        if assessment.average_tenure:
            lines.append(f"- 平均在籍年数: {assessment.average_tenure:.1f}年")
        
        # 評価結果
        lines.append("\n## 評価結果")
        lines.append(f"- 転職頻度: {assessment.job_change_frequency}")
        lines.append(f"- 安定性スコア: {assessment.stability_score:.0%}")
        lines.append(f"- 評価調整係数: {assessment.adjustment_factor:.2f}")
        
        # 説明
        lines.append("\n## 評価説明")
        lines.append(assessment.explanation)
        
        # リスク要因
        if assessment.risk_factors:
            lines.append("\n## リスク要因")
            for risk in assessment.risk_factors:
                lines.append(f"- ⚠️ {risk}")
        
        # 推奨事項
        if assessment.recommendations:
            lines.append("\n## 推奨事項")
            for rec in assessment.recommendations:
                lines.append(f"- {rec}")
        
        return '\n'.join(lines)