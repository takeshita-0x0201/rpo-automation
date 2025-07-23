"""
高度な検索戦略の実装
段階的検索、メタデータフィルタリング、結果の再ランキング
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
from collections import defaultdict


class AdvancedSearchStrategy:
    """高度な検索戦略を実装"""
    
    def __init__(self, vector_db):
        """
        Args:
            vector_db: UnifiedPineconeDBインスタンス
        """
        self.vector_db = vector_db
        self.search_stages = [
            "exact_position_match",
            "similar_position",
            "high_quality_cases",
            "recent_successful_cases",
            "cross_domain_insights"
        ]
        
    def execute_staged_search(
        self, 
        job_info: Dict,
        candidate_info: Dict,
        max_results: int = 50
    ) -> Dict:
        """
        段階的検索を実行
        
        Args:
            job_info: 求人情報
            candidate_info: 候補者情報
            max_results: 最大取得件数
            
        Returns:
            段階ごとの検索結果と統合結果
        """
        all_results = {
            "stages": {},
            "combined_results": [],
            "search_metadata": {
                "timestamp": datetime.now().isoformat(),
                "total_stages": len(self.search_stages)
            }
        }
        
        # Stage 1: 完全一致ポジション検索
        stage1_results = self._search_exact_position(
            job_info.get("position", ""),
            job_info,
            limit=20
        )
        all_results["stages"]["exact_position_match"] = stage1_results
        
        # Stage 2: 類似ポジション検索
        if len(stage1_results) < 10:
            stage2_results = self._search_similar_positions(
                job_info,
                exclude_ids=self._extract_case_ids(stage1_results),
                limit=15
            )
            all_results["stages"]["similar_position"] = stage2_results
        
        # Stage 3: 高品質事例検索
        stage3_results = self._search_high_quality_cases(
            job_info,
            candidate_info,
            exclude_ids=self._extract_all_case_ids(all_results),
            limit=10
        )
        all_results["stages"]["high_quality_cases"] = stage3_results
        
        # Stage 4: 最近の成功事例
        stage4_results = self._search_recent_successful_cases(
            job_info,
            days_back=90,
            exclude_ids=self._extract_all_case_ids(all_results),
            limit=10
        )
        all_results["stages"]["recent_successful_cases"] = stage4_results
        
        # Stage 5: クロスドメインインサイト
        if self._should_search_cross_domain(all_results):
            stage5_results = self._search_cross_domain_insights(
                candidate_info,
                exclude_ids=self._extract_all_case_ids(all_results),
                limit=5
            )
            all_results["stages"]["cross_domain_insights"] = stage5_results
        
        # 結果の統合と再ランキング
        all_results["combined_results"] = self._combine_and_rerank_results(
            all_results["stages"],
            job_info,
            candidate_info,
            max_results
        )
        
        # 検索品質メトリクスの計算
        all_results["search_metadata"]["quality_metrics"] = self._calculate_quality_metrics(
            all_results["combined_results"]
        )
        
        return all_results
        
    def _search_exact_position(self, position: str, job_info: Dict, limit: int) -> List[Dict]:
        """完全一致ポジション検索"""
        filters = {
            "position": {"$eq": position},
            "has_client_feedback": True
        }
        
        query_text = self._create_job_query_text(job_info)
        
        results = self.vector_db.search_similar_cases(
            query_text=query_text,
            filters=filters,
            top_k=limit,
            vector_type="job_side"
        )
        
        return self._enrich_results(results, "exact_position")
        
    def _search_similar_positions(self, job_info: Dict, exclude_ids: List[str], limit: int) -> List[Dict]:
        """類似ポジション検索"""
        # ポジション名から類似キーワードを抽出
        position_keywords = self._extract_position_keywords(job_info.get("position", ""))
        
        filters = {
            "has_client_feedback": True,
            "case_id": {"$nin": exclude_ids}
        }
        
        # 部門やジョブタイプでフィルタ
        if job_info.get("department"):
            filters["department"] = job_info["department"]
        if job_info.get("job_type"):
            filters["job_type"] = job_info["job_type"]
            
        query_text = self._create_job_query_text(job_info)
        
        results = self.vector_db.search_similar_cases(
            query_text=query_text,
            filters=filters,
            top_k=limit,
            vector_type="job_side"
        )
        
        # キーワードマッチングでスコアを調整
        for result in results:
            keyword_score = self._calculate_keyword_match_score(
                result["metadata"].get("position", ""),
                position_keywords
            )
            result["adjusted_score"] = result["score"] * (1 + keyword_score * 0.2)
            
        return self._enrich_results(results, "similar_position")
        
    def _search_high_quality_cases(
        self, 
        job_info: Dict, 
        candidate_info: Dict,
        exclude_ids: List[str],
        limit: int
    ) -> List[Dict]:
        """高品質事例の検索"""
        filters = {
            "is_successful": True,
            "has_detailed_feedback": True,
            "evaluation_match": True,  # AIと人間の評価が一致
            "score_category": {"$in": ["excellent", "good"]},
            "case_id": {"$nin": exclude_ids}
        }
        
        # 統合クエリテキスト
        query_text = self._create_combined_query_text(job_info, candidate_info)
        
        results = self.vector_db.search_similar_cases(
            query_text=query_text,
            filters=filters,
            top_k=limit,
            vector_type="combined"
        )
        
        return self._enrich_results(results, "high_quality")
        
    def _search_recent_successful_cases(
        self,
        job_info: Dict,
        days_back: int,
        exclude_ids: List[str],
        limit: int
    ) -> List[Dict]:
        """最近の成功事例を検索"""
        cutoff_date = (datetime.now() - timedelta(days=days_back)).isoformat()
        
        filters = {
            "is_successful": True,
            "created_at": {"$gte": cutoff_date},
            "case_id": {"$nin": exclude_ids}
        }
        
        query_text = self._create_job_query_text(job_info)
        
        results = self.vector_db.search_similar_cases(
            query_text=query_text,
            filters=filters,
            top_k=limit,
            vector_type="job_side"
        )
        
        # 新しさによるスコア調整
        for result in results:
            recency_score = self._calculate_recency_score(
                result["metadata"].get("created_at", "")
            )
            result["adjusted_score"] = result["score"] * (1 + recency_score * 0.1)
            
        return self._enrich_results(results, "recent_successful")
        
    def _search_cross_domain_insights(
        self,
        candidate_info: Dict,
        exclude_ids: List[str],
        limit: int
    ) -> List[Dict]:
        """クロスドメインインサイト検索"""
        filters = {
            "is_successful": True,
            "case_id": {"$nin": exclude_ids}
        }
        
        # 候補者のスキルや経験に基づく検索
        query_text = self._create_candidate_query_text(candidate_info)
        
        results = self.vector_db.search_similar_cases(
            query_text=query_text,
            filters=filters,
            top_k=limit,
            vector_type="candidate"
        )
        
        return self._enrich_results(results, "cross_domain")
        
    def _combine_and_rerank_results(
        self,
        staged_results: Dict,
        job_info: Dict,
        candidate_info: Dict,
        max_results: int
    ) -> List[Dict]:
        """結果を統合して再ランキング"""
        # 全結果を収集
        all_results = []
        case_id_to_results = defaultdict(list)
        
        for stage, results in staged_results.items():
            for result in results:
                case_id = result["metadata"]["case_id"]
                case_id_to_results[case_id].append({
                    "stage": stage,
                    "result": result
                })
                
        # 統合スコアの計算
        for case_id, occurrences in case_id_to_results.items():
            combined_score = self._calculate_combined_score(occurrences)
            
            # 最も関連性の高い出現を代表として使用
            best_occurrence = max(occurrences, key=lambda x: x["result"].get("adjusted_score", x["result"]["score"]))
            
            combined_result = {
                **best_occurrence["result"],
                "combined_score": combined_score,
                "appeared_in_stages": [occ["stage"] for occ in occurrences],
                "occurrence_count": len(occurrences)
            }
            
            all_results.append(combined_result)
            
        # 再ランキング
        all_results.sort(key=lambda x: x["combined_score"], reverse=True)
        
        # 重複除去と上位N件を返す
        return all_results[:max_results]
        
    def _calculate_combined_score(self, occurrences: List[Dict]) -> float:
        """統合スコアの計算"""
        # ステージごとの重み
        stage_weights = {
            "exact_position_match": 2.0,
            "similar_position": 1.5,
            "high_quality_cases": 1.8,
            "recent_successful_cases": 1.6,
            "cross_domain_insights": 1.2
        }
        
        total_score = 0
        total_weight = 0
        
        for occ in occurrences:
            stage = occ["stage"]
            result = occ["result"]
            score = result.get("adjusted_score", result["score"])
            weight = stage_weights.get(stage, 1.0)
            
            total_score += score * weight
            total_weight += weight
            
        # 出現回数によるボーナス
        occurrence_bonus = min(len(occurrences) * 0.1, 0.3)
        
        return (total_score / total_weight) * (1 + occurrence_bonus)
        
    def _calculate_quality_metrics(self, results: List[Dict]) -> Dict:
        """検索品質メトリクスの計算"""
        if not results:
            return {
                "avg_score": 0,
                "coverage": 0,
                "diversity": 0,
                "quality_rating": "low"
            }
            
        scores = [r["combined_score"] for r in results]
        positions = [r["metadata"].get("position", "") for r in results]
        
        metrics = {
            "avg_score": np.mean(scores),
            "score_std": np.std(scores),
            "coverage": len(set(positions)) / len(positions) if positions else 0,
            "high_quality_ratio": sum(1 for r in results if r["metadata"].get("is_successful")) / len(results),
            "recent_cases_ratio": sum(1 for r in results if self._is_recent(r["metadata"].get("created_at", ""))) / len(results)
        }
        
        # 総合評価
        if metrics["avg_score"] > 0.8 and metrics["high_quality_ratio"] > 0.6:
            metrics["quality_rating"] = "excellent"
        elif metrics["avg_score"] > 0.7 and metrics["high_quality_ratio"] > 0.4:
            metrics["quality_rating"] = "good"
        elif metrics["avg_score"] > 0.6:
            metrics["quality_rating"] = "fair"
        else:
            metrics["quality_rating"] = "low"
            
        return metrics
        
    # ヘルパーメソッド
    def _extract_case_ids(self, results: List[Dict]) -> List[str]:
        """結果からケースIDを抽出"""
        return [r["metadata"]["case_id"] for r in results]
        
    def _extract_all_case_ids(self, all_results: Dict) -> List[str]:
        """全ステージからケースIDを抽出"""
        case_ids = []
        for stage_results in all_results.get("stages", {}).values():
            case_ids.extend(self._extract_case_ids(stage_results))
        return list(set(case_ids))
        
    def _should_search_cross_domain(self, all_results: Dict) -> bool:
        """クロスドメイン検索を実行すべきか判定"""
        total_results = sum(len(results) for results in all_results.get("stages", {}).values())
        return total_results < 20
        
    def _enrich_results(self, results: List[Dict], stage: str) -> List[Dict]:
        """結果にステージ情報を追加"""
        for result in results:
            result["search_stage"] = stage
        return results
        
    def _extract_position_keywords(self, position: str) -> List[str]:
        """ポジション名からキーワードを抽出"""
        # 一般的な役職キーワード
        keywords = []
        position_lower = position.lower()
        
        if "manager" in position_lower or "マネージャー" in position:
            keywords.extend(["manager", "lead", "マネージャー", "リーダー"])
        if "engineer" in position_lower or "エンジニア" in position:
            keywords.extend(["engineer", "developer", "エンジニア", "開発"])
        if "senior" in position_lower or "シニア" in position:
            keywords.extend(["senior", "シニア", "上級"])
            
        return keywords
        
    def _calculate_keyword_match_score(self, text: str, keywords: List[str]) -> float:
        """キーワードマッチスコアを計算"""
        if not keywords:
            return 0
            
        matches = sum(1 for keyword in keywords if keyword.lower() in text.lower())
        return matches / len(keywords)
        
    def _calculate_recency_score(self, timestamp: str) -> float:
        """新しさスコアを計算"""
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            days_old = (datetime.now(dt.tzinfo) - dt).days
            
            if days_old <= 7:
                return 1.0
            elif days_old <= 30:
                return 0.8
            elif days_old <= 90:
                return 0.5
            else:
                return 0.2
        except:
            return 0
            
    def _is_recent(self, timestamp: str, days: int = 30) -> bool:
        """最近のデータかチェック"""
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            return (datetime.now(dt.tzinfo) - dt).days <= days
        except:
            return False
            
    def _create_job_query_text(self, job_info: Dict) -> str:
        """求人情報からクエリテキストを作成"""
        sections = []
        
        if job_info.get("position"):
            sections.append(f"ポジション: {job_info['position']}")
        if job_info.get("description"):
            sections.append(f"職務内容: {job_info['description'][:500]}")
        if job_info.get("required_skills"):
            sections.append(f"必須スキル: {', '.join(job_info['required_skills'])}")
            
        return "\n".join(sections)
        
    def _create_candidate_query_text(self, candidate_info: Dict) -> str:
        """候補者情報からクエリテキストを作成"""
        sections = []
        
        if candidate_info.get("skills"):
            sections.append(f"保有スキル: {', '.join(candidate_info['skills'])}")
        if candidate_info.get("experience"):
            sections.append(f"経験: {candidate_info['experience']}")
        if candidate_info.get("achievements"):
            sections.append(f"実績: {candidate_info['achievements'][:300]}")
            
        return "\n".join(sections)
        
    def _create_combined_query_text(self, job_info: Dict, candidate_info: Dict) -> str:
        """統合クエリテキストを作成"""
        job_text = self._create_job_query_text(job_info)
        candidate_text = self._create_candidate_query_text(candidate_info)
        
        return f"{job_text}\n\n{candidate_text}"