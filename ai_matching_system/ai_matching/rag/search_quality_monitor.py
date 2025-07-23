"""
ベクトル検索品質のモニタリングとレポート生成
"""

import os
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import numpy as np
import pandas as pd
from pathlib import Path


class SearchQualityMonitor:
    """検索品質をモニタリングし、改善のためのインサイトを提供"""
    
    def __init__(self, log_dir: str = "./search_logs"):
        """
        Args:
            log_dir: 検索ログを保存するディレクトリ
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # メトリクスの定義
        self.quality_metrics = {
            "relevance": "検索結果の関連性",
            "coverage": "求人要件のカバー率",
            "diversity": "結果の多様性",
            "recency": "データの新しさ",
            "user_satisfaction": "ユーザー満足度"
        }
        
    def log_search_session(
        self,
        session_id: str,
        search_query: Dict,
        search_results: Dict,
        user_feedback: Optional[Dict] = None
    ):
        """
        検索セッションをログに記録
        
        Args:
            session_id: セッションID
            search_query: 検索クエリ情報
            search_results: 検索結果
            user_feedback: ユーザーフィードバック（オプション）
        """
        log_entry = {
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "query": search_query,
            "results": self._summarize_results(search_results),
            "metrics": self._calculate_session_metrics(search_results),
            "user_feedback": user_feedback
        }
        
        # 日付ごとのログファイルに保存
        log_file = self.log_dir / f"search_log_{datetime.now().strftime('%Y%m%d')}.jsonl"
        
        with open(log_file, 'a', encoding='utf-8') as f:
            json.dump(log_entry, f, ensure_ascii=False)
            f.write('\n')
            
    def generate_quality_report(self, days: int = 7) -> Dict:
        """
        指定期間の検索品質レポートを生成
        
        Args:
            days: レポート対象の日数
            
        Returns:
            品質レポート
        """
        # ログデータを収集
        logs = self._collect_logs(days)
        
        if not logs:
            return {
                "status": "no_data",
                "message": f"過去{days}日間のデータがありません"
            }
            
        report = {
            "period": {
                "start": (datetime.now() - timedelta(days=days)).date().isoformat(),
                "end": datetime.now().date().isoformat(),
                "days": days
            },
            "summary": self._calculate_summary_statistics(logs),
            "quality_trends": self._analyze_quality_trends(logs),
            "problem_areas": self._identify_problem_areas(logs),
            "recommendations": self._generate_recommendations(logs),
            "detailed_metrics": self._calculate_detailed_metrics(logs)
        }
        
        return report
        
    def analyze_search_effectiveness(self, search_results: Dict) -> Dict:
        """
        個別の検索結果の効果を分析
        
        Args:
            search_results: 検索結果
            
        Returns:
            効果分析結果
        """
        analysis = {
            "overall_score": 0,
            "strengths": [],
            "weaknesses": [],
            "metrics": {}
        }
        
        # 各メトリクスを計算
        metrics = {
            "relevance_score": self._calculate_relevance_score(search_results),
            "coverage_score": self._calculate_coverage_score(search_results),
            "diversity_score": self._calculate_diversity_score(search_results),
            "recency_score": self._calculate_recency_score(search_results),
            "confidence_score": self._calculate_confidence_score(search_results)
        }
        
        analysis["metrics"] = metrics
        
        # 総合スコア
        analysis["overall_score"] = np.mean(list(metrics.values()))
        
        # 強みと弱みの識別
        for metric, score in metrics.items():
            if score >= 0.8:
                analysis["strengths"].append({
                    "metric": metric,
                    "score": score,
                    "description": self._get_metric_description(metric, score)
                })
            elif score < 0.6:
                analysis["weaknesses"].append({
                    "metric": metric,
                    "score": score,
                    "description": self._get_metric_description(metric, score),
                    "improvement": self._get_improvement_suggestion(metric, score)
                })
                
        return analysis
        
    def _calculate_relevance_score(self, search_results: Dict) -> float:
        """関連性スコアを計算"""
        combined_results = search_results.get("combined_results", [])
        
        if not combined_results:
            return 0.0
            
        # 上位結果の平均スコア
        top_scores = [r.get("combined_score", r.get("score", 0)) for r in combined_results[:10]]
        
        # 閾値ベースの評価
        high_relevance = sum(1 for s in top_scores if s > 0.8)
        medium_relevance = sum(1 for s in top_scores if 0.6 <= s <= 0.8)
        
        relevance_score = (high_relevance * 1.0 + medium_relevance * 0.5) / len(top_scores)
        
        return min(relevance_score, 1.0)
        
    def _calculate_coverage_score(self, search_results: Dict) -> float:
        """カバレッジスコアを計算"""
        stages = search_results.get("stages", {})
        
        # 各ステージでの結果数
        stage_coverage = {
            "exact_position_match": len(stages.get("exact_position_match", [])),
            "similar_position": len(stages.get("similar_position", [])),
            "high_quality_cases": len(stages.get("high_quality_cases", []))
        }
        
        # 重要なステージでの十分な結果があるか
        coverage_score = 0
        if stage_coverage["exact_position_match"] >= 5:
            coverage_score += 0.4
        elif stage_coverage["exact_position_match"] >= 3:
            coverage_score += 0.2
            
        if stage_coverage["similar_position"] >= 5:
            coverage_score += 0.3
            
        if stage_coverage["high_quality_cases"] >= 3:
            coverage_score += 0.3
            
        return coverage_score
        
    def _calculate_diversity_score(self, search_results: Dict) -> float:
        """多様性スコアを計算"""
        combined_results = search_results.get("combined_results", [])
        
        if len(combined_results) < 2:
            return 0.0
            
        # ポジションの多様性
        positions = [r["metadata"].get("position", "") for r in combined_results[:20]]
        unique_positions = len(set(positions))
        position_diversity = min(unique_positions / 5, 1.0)  # 5種類以上で最高スコア
        
        # 企業の多様性
        companies = [r["metadata"].get("company", "") for r in combined_results[:20]]
        unique_companies = len(set(companies))
        company_diversity = min(unique_companies / 10, 1.0)  # 10社以上で最高スコア
        
        # 時期の多様性
        periods = [r["metadata"].get("evaluation_period", "") for r in combined_results[:20]]
        unique_periods = len(set(periods))
        period_diversity = min(unique_periods / 6, 1.0)  # 6ヶ月以上で最高スコア
        
        return np.mean([position_diversity, company_diversity, period_diversity])
        
    def _calculate_recency_score(self, search_results: Dict) -> float:
        """新しさスコアを計算"""
        combined_results = search_results.get("combined_results", [])
        
        if not combined_results:
            return 0.0
            
        recent_counts = {
            "last_week": 0,
            "last_month": 0,
            "last_quarter": 0
        }
        
        now = datetime.now()
        
        for result in combined_results[:20]:
            created_at = result["metadata"].get("created_at", "")
            try:
                dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                days_old = (now - dt.replace(tzinfo=None)).days
                
                if days_old <= 7:
                    recent_counts["last_week"] += 1
                elif days_old <= 30:
                    recent_counts["last_month"] += 1
                elif days_old <= 90:
                    recent_counts["last_quarter"] += 1
            except:
                continue
                
        # 重み付けスコア
        recency_score = (
            recent_counts["last_week"] * 1.0 +
            recent_counts["last_month"] * 0.5 +
            recent_counts["last_quarter"] * 0.25
        ) / len(combined_results[:20])
        
        return min(recency_score, 1.0)
        
    def _calculate_confidence_score(self, search_results: Dict) -> float:
        """信頼度スコアを計算"""
        combined_results = search_results.get("combined_results", [])
        
        if not combined_results:
            return 0.0
            
        # 高品質データの割合
        high_quality_count = sum(
            1 for r in combined_results[:20]
            if r["metadata"].get("has_detailed_feedback") and 
            r["metadata"].get("evaluation_match")
        )
        
        # 複数ステージ出現の割合
        multi_stage_count = sum(
            1 for r in combined_results[:10]
            if len(r.get("appeared_in_stages", [])) > 1
        )
        
        quality_ratio = high_quality_count / len(combined_results[:20])
        multi_stage_ratio = multi_stage_count / len(combined_results[:10])
        
        return np.mean([quality_ratio, multi_stage_ratio])
        
    def _summarize_results(self, search_results: Dict) -> Dict:
        """検索結果のサマリーを作成"""
        combined_results = search_results.get("combined_results", [])
        stages = search_results.get("stages", {})
        
        return {
            "total_results": len(combined_results),
            "stages_summary": {
                stage: len(results) for stage, results in stages.items()
            },
            "top_scores": [r.get("combined_score", r.get("score", 0)) for r in combined_results[:5]],
            "quality_metrics": search_results.get("search_metadata", {}).get("quality_metrics", {})
        }
        
    def _calculate_session_metrics(self, search_results: Dict) -> Dict:
        """セッションメトリクスを計算"""
        return {
            "relevance": self._calculate_relevance_score(search_results),
            "coverage": self._calculate_coverage_score(search_results),
            "diversity": self._calculate_diversity_score(search_results),
            "recency": self._calculate_recency_score(search_results),
            "confidence": self._calculate_confidence_score(search_results)
        }
        
    def _collect_logs(self, days: int) -> List[Dict]:
        """指定期間のログを収集"""
        logs = []
        
        for i in range(days):
            date = datetime.now() - timedelta(days=i)
            log_file = self.log_dir / f"search_log_{date.strftime('%Y%m%d')}.jsonl"
            
            if log_file.exists():
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            logs.append(json.loads(line))
                        except:
                            continue
                            
        return logs
        
    def _calculate_summary_statistics(self, logs: List[Dict]) -> Dict:
        """サマリー統計を計算"""
        total_searches = len(logs)
        
        # メトリクスの集計
        all_metrics = defaultdict(list)
        for log in logs:
            metrics = log.get("metrics", {})
            for metric, value in metrics.items():
                all_metrics[metric].append(value)
                
        # 平均スコアの計算
        avg_metrics = {
            metric: np.mean(values) for metric, values in all_metrics.items()
        }
        
        # ユーザー満足度（フィードバックがある場合）
        satisfaction_scores = [
            log["user_feedback"]["satisfaction"]
            for log in logs
            if log.get("user_feedback", {}).get("satisfaction") is not None
        ]
        
        return {
            "total_searches": total_searches,
            "avg_metrics": avg_metrics,
            "user_satisfaction": np.mean(satisfaction_scores) if satisfaction_scores else None,
            "feedback_rate": len(satisfaction_scores) / total_searches if total_searches > 0 else 0
        }
        
    def _analyze_quality_trends(self, logs: List[Dict]) -> Dict:
        """品質トレンドを分析"""
        # 日別のメトリクスを集計
        daily_metrics = defaultdict(lambda: defaultdict(list))
        
        for log in logs:
            date = log["timestamp"][:10]  # YYYY-MM-DD
            metrics = log.get("metrics", {})
            
            for metric, value in metrics.items():
                daily_metrics[date][metric].append(value)
                
        # 日別平均を計算
        trends = {}
        for date, metrics in sorted(daily_metrics.items()):
            trends[date] = {
                metric: np.mean(values) for metric, values in metrics.items()
            }
            
        return trends
        
    def _identify_problem_areas(self, logs: List[Dict]) -> List[Dict]:
        """問題のある領域を特定"""
        problems = []
        
        # 低スコアのメトリクスを集計
        low_score_counts = defaultdict(int)
        
        for log in logs:
            metrics = log.get("metrics", {})
            for metric, value in metrics.items():
                if value < 0.6:
                    low_score_counts[metric] += 1
                    
        # 問題の多いメトリクスを特定
        total_searches = len(logs)
        
        for metric, count in low_score_counts.items():
            problem_rate = count / total_searches
            if problem_rate > 0.3:  # 30%以上で問題あり
                problems.append({
                    "metric": metric,
                    "problem_rate": problem_rate,
                    "severity": "high" if problem_rate > 0.5 else "medium",
                    "description": f"{metric}が低い検索が{problem_rate*100:.1f}%存在"
                })
                
        return sorted(problems, key=lambda x: x["problem_rate"], reverse=True)
        
    def _generate_recommendations(self, logs: List[Dict]) -> List[Dict]:
        """改善推奨事項を生成"""
        recommendations = []
        
        # サマリー統計を取得
        summary = self._calculate_summary_statistics(logs)
        avg_metrics = summary.get("avg_metrics", {})
        
        # 各メトリクスに基づく推奨事項
        if avg_metrics.get("relevance", 1.0) < 0.7:
            recommendations.append({
                "priority": "high",
                "area": "relevance",
                "recommendation": "埋め込みモデルの再トレーニングまたはクエリ最適化を検討",
                "expected_impact": "検索精度の向上"
            })
            
        if avg_metrics.get("coverage", 1.0) < 0.6:
            recommendations.append({
                "priority": "high",
                "area": "coverage",
                "recommendation": "過去データの追加収集と同期処理の実行",
                "expected_impact": "参照可能なケースの増加"
            })
            
        if avg_metrics.get("diversity", 1.0) < 0.5:
            recommendations.append({
                "priority": "medium",
                "area": "diversity",
                "recommendation": "検索フィルターの調整と類似度閾値の見直し",
                "expected_impact": "より幅広い参考事例の提供"
            })
            
        if avg_metrics.get("recency", 1.0) < 0.6:
            recommendations.append({
                "priority": "medium",
                "area": "recency",
                "recommendation": "同期頻度の増加と古いデータの重み付け調整",
                "expected_impact": "最新トレンドの反映"
            })
            
        return recommendations
        
    def _calculate_detailed_metrics(self, logs: List[Dict]) -> Dict:
        """詳細メトリクスを計算"""
        # 検索ステージ別の統計
        stage_stats = defaultdict(lambda: {"count": 0, "avg_results": []})
        
        for log in logs:
            stages_summary = log.get("results", {}).get("stages_summary", {})
            for stage, count in stages_summary.items():
                stage_stats[stage]["count"] += 1
                stage_stats[stage]["avg_results"].append(count)
                
        # 平均を計算
        for stage, stats in stage_stats.items():
            stats["avg_results"] = np.mean(stats["avg_results"]) if stats["avg_results"] else 0
            
        return {
            "stage_statistics": dict(stage_stats),
            "metric_distributions": self._calculate_metric_distributions(logs)
        }
        
    def _calculate_metric_distributions(self, logs: List[Dict]) -> Dict:
        """メトリクスの分布を計算"""
        distributions = defaultdict(list)
        
        for log in logs:
            metrics = log.get("metrics", {})
            for metric, value in metrics.items():
                distributions[metric].append(value)
                
        # 分布統計を計算
        distribution_stats = {}
        for metric, values in distributions.items():
            if values:
                distribution_stats[metric] = {
                    "mean": np.mean(values),
                    "std": np.std(values),
                    "min": np.min(values),
                    "max": np.max(values),
                    "percentiles": {
                        "25": np.percentile(values, 25),
                        "50": np.percentile(values, 50),
                        "75": np.percentile(values, 75)
                    }
                }
                
        return distribution_stats
        
    def _get_metric_description(self, metric: str, score: float) -> str:
        """メトリクスの説明を取得"""
        descriptions = {
            "relevance_score": f"検索結果の関連性: {score:.2f}",
            "coverage_score": f"求人要件のカバー率: {score:.2f}",
            "diversity_score": f"結果の多様性: {score:.2f}",
            "recency_score": f"データの新しさ: {score:.2f}",
            "confidence_score": f"結果の信頼度: {score:.2f}"
        }
        
        return descriptions.get(metric, f"{metric}: {score:.2f}")
        
    def _get_improvement_suggestion(self, metric: str, score: float) -> str:
        """改善提案を取得"""
        suggestions = {
            "relevance_score": "クエリの構造化を改善し、重要キーワードを強調",
            "coverage_score": "データ収集頻度を増やし、過去データを追加同期",
            "diversity_score": "検索パラメータを調整し、より幅広い結果を取得",
            "recency_score": "リアルタイム同期を有効化し、最新データを優先",
            "confidence_score": "高品質フィードバックの収集を強化"
        }
        
        return suggestions.get(metric, "メトリクスの詳細分析が必要")
        
    def export_report(self, report: Dict, format: str = "json") -> str:
        """レポートをエクスポート"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"quality_report_{timestamp}.{format}"
        filepath = self.log_dir / filename
        
        if format == "json":
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
        elif format == "csv":
            # CSVフォーマットでの出力（簡易版）
            df = pd.DataFrame([report["summary"]])
            df.to_csv(filepath, index=False, encoding='utf-8-sig')
            
        return str(filepath)