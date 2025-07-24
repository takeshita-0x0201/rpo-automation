"""
メタ学習による自己改善機能
過去の評価結果からパターンを学習し、精度向上を図る
"""

import json
import os
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import numpy as np
from collections import defaultdict
import pickle


@dataclass
class EvaluationFeedback:
    """評価フィードバック"""
    evaluation_id: str
    predicted_score: int
    actual_outcome: str  # "hired", "rejected", "withdrawn"
    feedback_date: datetime
    job_category: str
    candidate_profile: Dict[str, Any]
    evaluation_features: Dict[str, float]


@dataclass
class LearningPattern:
    """学習パターン"""
    pattern_type: str
    feature_importance: Dict[str, float]
    success_indicators: List[str]
    failure_indicators: List[str]
    confidence: float
    sample_count: int


@dataclass
class MetaLearningReport:
    """メタ学習レポート"""
    total_feedbacks: int
    accuracy_improvement: float
    key_patterns: List[LearningPattern]
    recommendations: List[str]
    next_review_date: datetime


class MetaLearner:
    """メタ学習器"""
    
    def __init__(self, storage_path: str = "./meta_learning_data"):
        self.storage_path = storage_path
        os.makedirs(storage_path, exist_ok=True)
        
        # 学習データの読み込み
        self.feedbacks = self._load_feedbacks()
        self.patterns = self._load_patterns()
        
        # 特徴重要度
        self.feature_weights = {
            "skill_match": 1.0,
            "experience_match": 1.0,
            "company_size_match": 1.0,
            "salary_match": 1.0,
            "location_match": 1.0,
            "culture_fit": 1.0
        }
        
        # 業界別の成功パターン
        self.industry_patterns = defaultdict(list)
        
        # 学習パラメータ
        self.min_samples_for_pattern = 10
        self.confidence_threshold = 0.7
        self.learning_rate = 0.1
    
    def add_feedback(self, feedback: EvaluationFeedback) -> None:
        """評価フィードバックを追加"""
        self.feedbacks.append(feedback)
        self._save_feedbacks()
        
        # パターンを更新
        if len(self.feedbacks) >= self.min_samples_for_pattern:
            self._update_patterns()
    
    def learn_from_history(self) -> MetaLearningReport:
        """過去の履歴から学習"""
        if len(self.feedbacks) < self.min_samples_for_pattern:
            return MetaLearningReport(
                total_feedbacks=len(self.feedbacks),
                accuracy_improvement=0.0,
                key_patterns=[],
                recommendations=[f"学習には最低{self.min_samples_for_pattern}件のフィードバックが必要です"],
                next_review_date=datetime.now() + timedelta(days=30)
            )
        
        # 1. 予測精度を計算
        accuracy_before, accuracy_after = self._calculate_accuracy_improvement()
        
        # 2. 重要なパターンを抽出
        key_patterns = self._extract_key_patterns()
        
        # 3. 特徴重要度を更新
        self._update_feature_weights()
        
        # 4. 推奨事項を生成
        recommendations = self._generate_recommendations(key_patterns)
        
        # 5. パターンを保存
        self._save_patterns()
        
        return MetaLearningReport(
            total_feedbacks=len(self.feedbacks),
            accuracy_improvement=accuracy_after - accuracy_before,
            key_patterns=key_patterns,
            recommendations=recommendations,
            next_review_date=datetime.now() + timedelta(days=7)
        )
    
    def get_adjusted_weights(self, job_category: str) -> Dict[str, float]:
        """調整された重みを取得"""
        base_weights = self.feature_weights.copy()
        
        # 業界特有のパターンを適用
        if job_category in self.industry_patterns:
            patterns = self.industry_patterns[job_category]
            for pattern in patterns:
                if pattern.confidence >= self.confidence_threshold:
                    for feature, importance in pattern.feature_importance.items():
                        if feature in base_weights:
                            base_weights[feature] *= (1 + importance * self.learning_rate)
        
        # 正規化
        total = sum(base_weights.values())
        if total > 0:
            for key in base_weights:
                base_weights[key] /= total
        
        return base_weights
    
    def predict_success_probability(self, 
                                  evaluation_score: int,
                                  job_category: str,
                                  features: Dict[str, float]) -> float:
        """採用成功確率を予測"""
        # 基本確率（スコアベース）
        base_probability = evaluation_score / 100.0
        
        # パターンベースの調整
        if job_category in self.industry_patterns:
            patterns = self.industry_patterns[job_category]
            adjustments = []
            
            for pattern in patterns:
                if pattern.confidence >= self.confidence_threshold:
                    # 成功指標との一致度
                    success_match = self._calculate_pattern_match(
                        features, pattern.success_indicators
                    )
                    # 失敗指標との一致度
                    failure_match = self._calculate_pattern_match(
                        features, pattern.failure_indicators
                    )
                    
                    adjustment = (success_match - failure_match) * pattern.confidence
                    adjustments.append(adjustment)
            
            if adjustments:
                avg_adjustment = np.mean(adjustments)
                base_probability = np.clip(
                    base_probability + avg_adjustment * 0.2, 0.0, 1.0
                )
        
        return base_probability
    
    def _update_patterns(self) -> None:
        """パターンを更新"""
        # 業界別にフィードバックをグループ化
        category_feedbacks = defaultdict(list)
        for feedback in self.feedbacks:
            category_feedbacks[feedback.job_category].append(feedback)
        
        # 各業界のパターンを分析
        for category, feedbacks in category_feedbacks.items():
            if len(feedbacks) >= self.min_samples_for_pattern:
                patterns = self._analyze_category_patterns(category, feedbacks)
                self.industry_patterns[category] = patterns
    
    def _analyze_category_patterns(self, 
                                  category: str,
                                  feedbacks: List[EvaluationFeedback]) -> List[LearningPattern]:
        """カテゴリ別のパターンを分析"""
        patterns = []
        
        # 成功/失敗を分離
        successful = [f for f in feedbacks if f.actual_outcome == "hired"]
        unsuccessful = [f for f in feedbacks if f.actual_outcome == "rejected"]
        
        if len(successful) >= 5 and len(unsuccessful) >= 5:
            # 特徴重要度を計算
            feature_importance = self._calculate_feature_importance(
                successful, unsuccessful
            )
            
            # 成功/失敗指標を抽出
            success_indicators = self._extract_indicators(successful, True)
            failure_indicators = self._extract_indicators(unsuccessful, False)
            
            # 確信度を計算
            confidence = self._calculate_pattern_confidence(
                len(successful), len(unsuccessful), len(feedbacks)
            )
            
            pattern = LearningPattern(
                pattern_type=f"{category}_hiring_pattern",
                feature_importance=feature_importance,
                success_indicators=success_indicators,
                failure_indicators=failure_indicators,
                confidence=confidence,
                sample_count=len(feedbacks)
            )
            
            patterns.append(pattern)
        
        return patterns
    
    def _calculate_feature_importance(self,
                                    successful: List[EvaluationFeedback],
                                    unsuccessful: List[EvaluationFeedback]) -> Dict[str, float]:
        """特徴重要度を計算"""
        importance = {}
        
        # 各特徴の平均値を計算
        for feature in self.feature_weights.keys():
            success_values = [
                f.evaluation_features.get(feature, 0) for f in successful
            ]
            unsuccess_values = [
                f.evaluation_features.get(feature, 0) for f in unsuccessful
            ]
            
            if success_values and unsuccess_values:
                # 平均値の差
                diff = np.mean(success_values) - np.mean(unsuccess_values)
                # 標準偏差で正規化
                std = np.std(success_values + unsuccess_values)
                if std > 0:
                    importance[feature] = abs(diff) / std
                else:
                    importance[feature] = 0.0
        
        # 正規化
        total = sum(importance.values())
        if total > 0:
            for key in importance:
                importance[key] /= total
        
        return importance
    
    def _extract_indicators(self,
                          feedbacks: List[EvaluationFeedback],
                          is_success: bool) -> List[str]:
        """指標を抽出"""
        indicators = []
        
        # スコア範囲
        scores = [f.predicted_score for f in feedbacks]
        if scores:
            avg_score = np.mean(scores)
            if is_success:
                indicators.append(f"スコア{int(avg_score)}点以上")
            else:
                indicators.append(f"スコア{int(avg_score)}点以下")
        
        # 主要な特徴
        for feature in ["skill_match", "experience_match", "culture_fit"]:
            values = [f.evaluation_features.get(feature, 0) for f in feedbacks]
            if values:
                avg_value = np.mean(values)
                if avg_value > 0.7:
                    indicators.append(f"{feature}が高い")
                elif avg_value < 0.3:
                    indicators.append(f"{feature}が低い")
        
        return indicators[:5]  # 最大5つ
    
    def _calculate_pattern_confidence(self,
                                    success_count: int,
                                    failure_count: int,
                                    total_count: int) -> float:
        """パターンの確信度を計算"""
        # サンプル数に基づく基本確信度
        sample_confidence = min(total_count / 100, 1.0)
        
        # バランスに基づく確信度
        balance_ratio = min(success_count, failure_count) / max(success_count, failure_count)
        balance_confidence = balance_ratio
        
        # 総合確信度
        return sample_confidence * 0.7 + balance_confidence * 0.3
    
    def _calculate_accuracy_improvement(self) -> Tuple[float, float]:
        """精度改善を計算"""
        if len(self.feedbacks) < 20:
            return 0.0, 0.0
        
        # 初期の精度（最初の20%）
        early_count = max(int(len(self.feedbacks) * 0.2), 10)
        early_feedbacks = self.feedbacks[:early_count]
        
        early_correct = sum(
            1 for f in early_feedbacks
            if (f.predicted_score >= 70 and f.actual_outcome == "hired") or
               (f.predicted_score < 70 and f.actual_outcome == "rejected")
        )
        early_accuracy = early_correct / len(early_feedbacks)
        
        # 現在の精度（最後の20%）
        recent_count = max(int(len(self.feedbacks) * 0.2), 10)
        recent_feedbacks = self.feedbacks[-recent_count:]
        
        recent_correct = sum(
            1 for f in recent_feedbacks
            if (f.predicted_score >= 70 and f.actual_outcome == "hired") or
               (f.predicted_score < 70 and f.actual_outcome == "rejected")
        )
        recent_accuracy = recent_correct / len(recent_feedbacks)
        
        return early_accuracy, recent_accuracy
    
    def _extract_key_patterns(self) -> List[LearningPattern]:
        """重要なパターンを抽出"""
        all_patterns = []
        for patterns in self.industry_patterns.values():
            all_patterns.extend(patterns)
        
        # 確信度でソート
        all_patterns.sort(key=lambda p: p.confidence, reverse=True)
        
        return all_patterns[:5]  # 上位5つ
    
    def _update_feature_weights(self) -> None:
        """特徴重みを更新"""
        # 全パターンの特徴重要度を集計
        aggregated_importance = defaultdict(list)
        
        for patterns in self.industry_patterns.values():
            for pattern in patterns:
                if pattern.confidence >= self.confidence_threshold:
                    for feature, importance in pattern.feature_importance.items():
                        aggregated_importance[feature].append(importance)
        
        # 平均化して更新
        for feature in self.feature_weights:
            if feature in aggregated_importance:
                avg_importance = np.mean(aggregated_importance[feature])
                # 学習率を適用
                self.feature_weights[feature] = (
                    self.feature_weights[feature] * (1 - self.learning_rate) +
                    avg_importance * self.learning_rate
                )
    
    def _generate_recommendations(self, patterns: List[LearningPattern]) -> List[str]:
        """推奨事項を生成"""
        recommendations = []
        
        # 特徴重要度に基づく推奨
        sorted_features = sorted(
            self.feature_weights.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        top_feature = sorted_features[0][0]
        recommendations.append(
            f"最も重要な評価要素は'{top_feature}'です。この要素を重点的に評価してください。"
        )
        
        # パターンに基づく推奨
        if patterns:
            top_pattern = patterns[0]
            if top_pattern.success_indicators:
                recommendations.append(
                    f"成功事例の共通点: {', '.join(top_pattern.success_indicators[:3])}"
                )
            if top_pattern.failure_indicators:
                recommendations.append(
                    f"失敗事例の共通点: {', '.join(top_pattern.failure_indicators[:3])}"
                )
        
        # 精度改善に関する推奨
        _, recent_accuracy = self._calculate_accuracy_improvement()
        if recent_accuracy < 0.7:
            recommendations.append(
                "予測精度が低いため、評価基準の見直しを検討してください。"
            )
        
        return recommendations
    
    def _calculate_pattern_match(self,
                               features: Dict[str, float],
                               indicators: List[str]) -> float:
        """パターンとの一致度を計算"""
        if not indicators:
            return 0.0
        
        matches = 0
        for indicator in indicators:
            # 簡易的なマッチング
            if "高い" in indicator:
                feature_name = indicator.split("が")[0]
                if feature_name in features and features[feature_name] > 0.7:
                    matches += 1
            elif "低い" in indicator:
                feature_name = indicator.split("が")[0]
                if feature_name in features and features[feature_name] < 0.3:
                    matches += 1
            elif "点以上" in indicator:
                score = int(indicator.split("スコア")[1].split("点")[0])
                if features.get("predicted_score", 0) >= score:
                    matches += 1
            elif "点以下" in indicator:
                score = int(indicator.split("スコア")[1].split("点")[0])
                if features.get("predicted_score", 0) <= score:
                    matches += 1
        
        return matches / len(indicators)
    
    def _load_feedbacks(self) -> List[EvaluationFeedback]:
        """フィードバックを読み込み"""
        filepath = os.path.join(self.storage_path, "feedbacks.pkl")
        if os.path.exists(filepath):
            with open(filepath, "rb") as f:
                return pickle.load(f)
        return []
    
    def _save_feedbacks(self) -> None:
        """フィードバックを保存"""
        filepath = os.path.join(self.storage_path, "feedbacks.pkl")
        with open(filepath, "wb") as f:
            pickle.dump(self.feedbacks, f)
    
    def _load_patterns(self) -> Dict[str, List[LearningPattern]]:
        """パターンを読み込み"""
        filepath = os.path.join(self.storage_path, "patterns.pkl")
        if os.path.exists(filepath):
            with open(filepath, "rb") as f:
                return pickle.load(f)
        return {}
    
    def _save_patterns(self) -> None:
        """パターンを保存"""
        filepath = os.path.join(self.storage_path, "patterns.pkl")
        with open(filepath, "wb") as f:
            pickle.dump(dict(self.industry_patterns), f)
    
    def format_learning_report(self, report: MetaLearningReport) -> str:
        """学習レポートをフォーマット"""
        lines = []
        lines.append("# メタ学習レポート")
        lines.append(f"\n総フィードバック数: {report.total_feedbacks}")
        lines.append(f"精度改善: {report.accuracy_improvement:+.1%}")
        lines.append(f"次回レビュー日: {report.next_review_date.strftime('%Y-%m-%d')}")
        
        if report.key_patterns:
            lines.append("\n## 重要なパターン")
            for i, pattern in enumerate(report.key_patterns, 1):
                lines.append(f"\n### パターン{i}: {pattern.pattern_type}")
                lines.append(f"確信度: {pattern.confidence:.0%}")
                lines.append(f"サンプル数: {pattern.sample_count}")
                
                if pattern.feature_importance:
                    lines.append("\n特徴重要度:")
                    sorted_features = sorted(
                        pattern.feature_importance.items(),
                        key=lambda x: x[1],
                        reverse=True
                    )
                    for feature, importance in sorted_features[:3]:
                        lines.append(f"- {feature}: {importance:.2f}")
                
                if pattern.success_indicators:
                    lines.append("\n成功指標:")
                    for indicator in pattern.success_indicators[:3]:
                        lines.append(f"- {indicator}")
                
                if pattern.failure_indicators:
                    lines.append("\n失敗指標:")
                    for indicator in pattern.failure_indicators[:3]:
                        lines.append(f"- {indicator}")
        
        if report.recommendations:
            lines.append("\n## 推奨事項")
            for rec in report.recommendations:
                lines.append(f"- {rec}")
        
        return '\n'.join(lines)