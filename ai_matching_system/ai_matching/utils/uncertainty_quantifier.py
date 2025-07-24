"""
不確実性の定量化メカニズム
評価の不確実性を数値化し、情報不足による判断の曖昧さを明示
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import re
import math


@dataclass
class UncertaintyFactors:
    """不確実性の要因"""
    missing_information: float = 0.0  # 情報欠如による不確実性
    ambiguous_experience: float = 0.0  # 経験の曖昧さによる不確実性
    contradictory_signals: float = 0.0  # 矛盾するシグナルによる不確実性
    indirect_evidence: float = 0.0  # 間接的証拠による不確実性
    temporal_uncertainty: float = 0.0  # 時間経過による不確実性
    
    @property
    def total_uncertainty(self) -> float:
        """総合的な不確実性（0.0-1.0）"""
        # 各要因を重み付けして合計
        weighted_sum = (
            self.missing_information * 0.3 +
            self.ambiguous_experience * 0.25 +
            self.contradictory_signals * 0.2 +
            self.indirect_evidence * 0.15 +
            self.temporal_uncertainty * 0.1
        )
        return min(weighted_sum, 1.0)
    
    @property
    def confidence_level(self) -> float:
        """確信度レベル（0.0-1.0）"""
        return 1.0 - self.total_uncertainty


@dataclass
class UncertaintyReport:
    """不確実性レポート"""
    factors: UncertaintyFactors
    confidence_level: float
    uncertainty_level: str  # "低", "中", "高"
    key_uncertainties: List[str]
    recommendations: List[str]


class UncertaintyQuantifier:
    """不確実性定量化器"""
    
    def __init__(self):
        # 不確実性を示すキーワード
        self.uncertainty_keywords = {
            "推測": 0.8,
            "可能性": 0.7,
            "思われる": 0.7,
            "かもしれない": 0.8,
            "不明": 0.9,
            "確認できない": 0.8,
            "判断が難しい": 0.7,
            "明確でない": 0.7,
            "曖昧": 0.8,
            "おそらく": 0.6,
            "恐らく": 0.6,
            "だろう": 0.6,
            "推定": 0.7,
            "想定": 0.7,
            "予想": 0.6
        }
        
        # 確実性を示すキーワード
        self.certainty_keywords = {
            "明確に": -0.3,
            "確実に": -0.4,
            "間違いなく": -0.4,
            "確認できる": -0.3,
            "実績あり": -0.3,
            "証明されている": -0.4,
            "具体的に": -0.2,
            "詳細に": -0.2
        }
        
        # 時間に関するパターン
        self.time_patterns = [
            (r'(\d+)年前', lambda years: min(int(years) * 0.1, 0.8)),  # 年数に応じて不確実性増加
            (r'最近', lambda: 0.1),
            (r'現在', lambda: 0.0),
            (r'過去に', lambda: 0.3),
            (r'以前', lambda: 0.4)
        ]
    
    def quantify_uncertainty(self, 
                           evaluation_text: str,
                           resume_text: str,
                           job_requirements: str,
                           search_results: Optional[Dict] = None) -> UncertaintyReport:
        """不確実性を定量化"""
        
        factors = UncertaintyFactors()
        
        # 1. 情報欠如による不確実性を評価
        factors.missing_information = self._assess_missing_information(
            resume_text, job_requirements, evaluation_text
        )
        
        # 2. 経験の曖昧さを評価
        factors.ambiguous_experience = self._assess_ambiguous_experience(
            resume_text, evaluation_text
        )
        
        # 3. 矛盾するシグナルを評価
        factors.contradictory_signals = self._assess_contradictions(
            evaluation_text, search_results
        )
        
        # 4. 間接的証拠による不確実性を評価
        factors.indirect_evidence = self._assess_indirect_evidence(
            resume_text, evaluation_text
        )
        
        # 5. 時間経過による不確実性を評価
        factors.temporal_uncertainty = self._assess_temporal_uncertainty(
            resume_text, evaluation_text
        )
        
        # レポート生成
        return self._generate_report(factors, evaluation_text)
    
    def _assess_missing_information(self, resume: str, requirements: str, evaluation: str) -> float:
        """情報欠如による不確実性を評価"""
        uncertainty = 0.0
        
        # 必須要件のキーワードを抽出
        required_keywords = self._extract_requirements(requirements)
        
        # レジュメでカバーされていない要件をカウント
        uncovered_count = 0
        for keyword in required_keywords:
            if keyword.lower() not in resume.lower():
                uncovered_count += 1
        
        if required_keywords:
            missing_ratio = uncovered_count / len(required_keywords)
            uncertainty += missing_ratio * 0.6
        
        # 評価文に「情報不足」「確認できない」などの表現があるか
        missing_phrases = ["情報が不足", "確認できない", "記載がない", "不明", "判断材料が少ない"]
        for phrase in missing_phrases:
            if phrase in evaluation:
                uncertainty += 0.2
                break
        
        return min(uncertainty, 1.0)
    
    def _assess_ambiguous_experience(self, resume: str, evaluation: str) -> float:
        """経験の曖昧さを評価"""
        uncertainty = 0.0
        
        # レジュメの曖昧な表現をカウント
        ambiguous_patterns = [
            r'関わった',  # 具体的な役割が不明
            r'サポート',  # 主体的でない可能性
            r'補助',
            r'一部',
            r'など',  # 具体性の欠如
            r'等',
            r'様々な',
            r'いくつかの',
            r'複数の'
        ]
        
        resume_lines = resume.split('\n')
        ambiguous_count = 0
        total_experience_lines = 0
        
        for line in resume_lines:
            if any(pattern in ['経験', '実績', '担当', '開発', 'プロジェクト'] for pattern in line):
                total_experience_lines += 1
                for pattern in ambiguous_patterns:
                    if re.search(pattern, line):
                        ambiguous_count += 1
                        break
        
        if total_experience_lines > 0:
            ambiguity_ratio = ambiguous_count / total_experience_lines
            uncertainty += ambiguity_ratio * 0.5
        
        # 評価文の不確実性キーワードをチェック
        for keyword, weight in self.uncertainty_keywords.items():
            if keyword in evaluation:
                uncertainty += weight * 0.1
        
        return min(uncertainty, 1.0)
    
    def _assess_contradictions(self, evaluation: str, search_results: Optional[Dict]) -> float:
        """矛盾するシグナルを評価"""
        uncertainty = 0.0
        
        # 評価文内の矛盾表現
        contradiction_patterns = [
            r'一方で',
            r'しかし',
            r'ただし',
            r'反面',
            r'逆に',
            r'矛盾',
            r'不一致'
        ]
        
        contradiction_count = sum(1 for pattern in contradiction_patterns if re.search(pattern, evaluation))
        uncertainty += contradiction_count * 0.15
        
        # 検索結果に矛盾があるか
        if search_results:
            for key, result in search_results.items():
                if '矛盾' in result.summary or '不一致' in result.summary:
                    uncertainty += 0.2
                    break
        
        return min(uncertainty, 1.0)
    
    def _assess_indirect_evidence(self, resume: str, evaluation: str) -> float:
        """間接的証拠による不確実性を評価"""
        uncertainty = 0.0
        
        # 間接的な経験を示す表現
        indirect_patterns = [
            r'類似',
            r'関連',
            r'近い',
            r'似た',
            r'代替',
            r'転用可能',
            r'応用可能'
        ]
        
        indirect_count = sum(1 for pattern in indirect_patterns if re.search(pattern, evaluation))
        uncertainty += indirect_count * 0.1
        
        # 直接的な証拠の欠如
        if "直接的な経験" in evaluation and "ない" in evaluation:
            uncertainty += 0.3
        
        return min(uncertainty, 1.0)
    
    def _assess_temporal_uncertainty(self, resume: str, evaluation: str) -> float:
        """時間経過による不確実性を評価"""
        uncertainty = 0.0
        max_years_ago = 0
        
        # 経験の時期を分析
        for pattern, uncertainty_func in self.time_patterns:
            matches = re.findall(pattern, resume + ' ' + evaluation)
            for match in matches:
                if isinstance(match, tuple):
                    years = match[0]
                    temp_uncertainty = uncertainty_func(years)
                else:
                    temp_uncertainty = uncertainty_func()
                uncertainty = max(uncertainty, temp_uncertainty)
        
        # 古い経験への言及
        if "過去の経験" in evaluation or "以前の" in evaluation:
            uncertainty = max(uncertainty, 0.3)
        
        return min(uncertainty, 1.0)
    
    def _extract_requirements(self, requirements: str) -> List[str]:
        """要件からキーワードを抽出"""
        keywords = []
        
        # 必須要件のパターン
        patterns = [
            r'必須[：:]\s*(.+?)(?:\n|$)',
            r'必要[：:]\s*(.+?)(?:\n|$)',
            r'求める[：:]\s*(.+?)(?:\n|$)',
            r'・\s*(.+?)(?:\n|$)'  # 箇条書き
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, requirements, re.MULTILINE)
            keywords.extend(matches)
        
        # 技術キーワードの抽出
        tech_pattern = r'[A-Za-z]+(?:\s*[A-Za-z]+)*|[ァ-ヴー]+(?:開発|経験|スキル)'
        tech_matches = re.findall(tech_pattern, requirements)
        keywords.extend(tech_matches)
        
        return list(set(keywords))[:20]  # 最大20個
    
    def _generate_report(self, factors: UncertaintyFactors, evaluation_text: str) -> UncertaintyReport:
        """不確実性レポートを生成"""
        confidence_level = factors.confidence_level
        
        # 不確実性レベルの判定
        if factors.total_uncertainty < 0.3:
            uncertainty_level = "低"
        elif factors.total_uncertainty < 0.6:
            uncertainty_level = "中"
        else:
            uncertainty_level = "高"
        
        # 主要な不確実性要因を特定
        key_uncertainties = []
        
        if factors.missing_information > 0.5:
            key_uncertainties.append("重要な情報が不足している")
        if factors.ambiguous_experience > 0.5:
            key_uncertainties.append("経験の詳細が曖昧である")
        if factors.contradictory_signals > 0.3:
            key_uncertainties.append("矛盾するシグナルが存在する")
        if factors.indirect_evidence > 0.4:
            key_uncertainties.append("直接的な証拠が不足している")
        if factors.temporal_uncertainty > 0.5:
            key_uncertainties.append("経験が古く現在の能力が不明確")
        
        # 推奨事項の生成
        recommendations = []
        
        if factors.missing_information > 0.5:
            recommendations.append("面接で不足情報を確認する")
        if factors.ambiguous_experience > 0.5:
            recommendations.append("具体的な実績と役割を詳細に確認する")
        if factors.contradictory_signals > 0.3:
            recommendations.append("矛盾点について本人に確認する")
        if factors.indirect_evidence > 0.4:
            recommendations.append("スキルチェックや実技試験を検討する")
        if factors.temporal_uncertainty > 0.5:
            recommendations.append("最近の経験とスキルレベルを確認する")
        
        return UncertaintyReport(
            factors=factors,
            confidence_level=confidence_level,
            uncertainty_level=uncertainty_level,
            key_uncertainties=key_uncertainties,
            recommendations=recommendations
        )
    
    def format_uncertainty_summary(self, report: UncertaintyReport) -> str:
        """不確実性サマリーをフォーマット"""
        summary = []
        
        summary.append(f"【評価の確信度】{report.confidence_level:.0%} (不確実性: {report.uncertainty_level})")
        
        if report.key_uncertainties:
            summary.append("\n【主な不確実性要因】")
            for uncertainty in report.key_uncertainties:
                summary.append(f"- {uncertainty}")
        
        if report.recommendations:
            summary.append("\n【推奨アクション】")
            for rec in report.recommendations:
                summary.append(f"- {rec}")
        
        # 詳細な要因分析
        summary.append("\n【不確実性の内訳】")
        summary.append(f"- 情報欠如: {report.factors.missing_information:.0%}")
        summary.append(f"- 経験の曖昧さ: {report.factors.ambiguous_experience:.0%}")
        summary.append(f"- 矛盾シグナル: {report.factors.contradictory_signals:.0%}")
        summary.append(f"- 間接的証拠: {report.factors.indirect_evidence:.0%}")
        summary.append(f"- 時間的要因: {report.factors.temporal_uncertainty:.0%}")
        
        return '\n'.join(summary)