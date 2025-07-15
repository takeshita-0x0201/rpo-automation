"""
ベクトルデータベース管理クラス（B案：複数ベクトル戦略）
"""

from typing import Dict, List, Optional, Tuple
import os
from datetime import datetime


class VectorManager:
    """
    評価ケースのベクトル化と管理を行う
    B案: 1ケースあたり複数のベクトルを保存
    """
    
    def __init__(self, index_name: str = "recruitment-rag"):
        self.index_name = index_name
        self.vectors_per_case = {
            "combined": "4要素統合（検索のメイン）",
            "job_side": "求人側（ポジション+求人票+メモ）",
            "candidate": "候補者側（レジュメのみ）"
        }
    
    def prepare_case_vectors(self, case_data: Dict) -> List[Dict]:
        """
        1つの評価ケースから複数のベクトルを準備
        
        Args:
            case_data: 評価ケースデータ
            
        Returns:
            Pineconeに保存するベクトルのリスト
        """
        vectors = []
        case_id = case_data.get('case_id', f"case_{datetime.now().timestamp()}")
        
        # 1. 統合ベクトル（メイン検索用）
        combined_text = f"""
ポジション: {case_data.get('position', '')}
求人内容:
{case_data.get('job_description', '')}
求人メモ:
{case_data.get('job_memo', '')}
候補者情報:
{case_data.get('resume', '')}
"""
        
        vectors.append({
            "id": f"{case_id}_combined",
            "text": combined_text,
            "metadata": {
                "case_id": case_id,
                "vector_type": "combined",
                "position": case_data.get('position', ''),
                "ai_recommendation": case_data.get('ai_evaluation', {}).get('recommendation', ''),
                "client_recommendation": case_data.get('client_evaluation', {}).get('recommendation', ''),
                "ai_score": case_data.get('ai_evaluation', {}).get('score', 0),
                "match": case_data.get('comparison', {}).get('match', False),
                "created_at": case_data.get('created_at', datetime.now().isoformat())
            }
        })
        
        # 2. 求人側ベクトル（ポジション検索用）
        job_side_text = f"""
ポジション: {case_data.get('position', '')}
{case_data.get('job_description', '')}
{case_data.get('job_memo', '')}
"""
        
        vectors.append({
            "id": f"{case_id}_job_side",
            "text": job_side_text,
            "metadata": {
                "case_id": case_id,
                "vector_type": "job_side",
                "position": case_data.get('position', ''),
                "created_at": case_data.get('created_at', datetime.now().isoformat())
            }
        })
        
        # 3. 候補者ベクトル（候補者プロファイル検索用）
        candidate_text = case_data.get('resume', '')
        
        vectors.append({
            "id": f"{case_id}_candidate",
            "text": candidate_text,
            "metadata": {
                "case_id": case_id,
                "vector_type": "candidate",
                "position": case_data.get('position', ''),  # 参考情報として含める
                "created_at": case_data.get('created_at', datetime.now().isoformat())
            }
        })
        
        return vectors
    
    def search_strategy_for_new_evaluation(self, position: str, job_desc: str, job_memo: str, resume: str) -> Dict:
        """
        新規評価時の検索戦略を決定
        
        Returns:
            検索戦略の詳細
        """
        strategy = {
            "searches": [],
            "position": position
        }
        
        # 1. まずポジション完全一致で求人側検索
        strategy["searches"].append({
            "name": "exact_position_match",
            "query_text": f"{position}\n{job_desc}\n{job_memo}",
            "vector_type": "job_side",
            "filters": {
                "position": position,
                "vector_type": "job_side"
            },
            "top_k": 10,
            "purpose": "同一ポジションの過去事例を検索"
        })
        
        # 2. 全体類似性検索（ポジション問わず）
        strategy["searches"].append({
            "name": "overall_similarity",
            "query_text": f"{position}\n{job_desc}\n{job_memo}\n{resume}",
            "vector_type": "combined",
            "filters": {
                "vector_type": "combined"
            },
            "top_k": 20,
            "purpose": "4要素全体で類似するケースを検索"
        })
        
        # 3. 高評価事例からの学習（オプション）
        strategy["searches"].append({
            "name": "success_patterns",
            "query_text": f"{position}\n{job_desc}\n{job_memo}\n{resume}",
            "vector_type": "combined",
            "filters": {
                "vector_type": "combined",
                "client_recommendation": {"$in": ["A", "B"]}
            },
            "top_k": 5,
            "purpose": "類似する成功事例を参考にする"
        })
        
        return strategy
    
    def determine_rag_usage(self, search_results: Dict) -> Tuple[bool, str]:
        """
        検索結果に基づいてRAG使用可否を判定
        
        Returns:
            (use_rag, reason)
        """
        exact_matches = search_results.get("exact_position_match", [])
        
        if len(exact_matches) >= 3:
            return True, f"同一ポジションで{len(exact_matches)}件の参照データあり"
        elif len(exact_matches) > 0:
            return True, f"同一ポジションのデータは{len(exact_matches)}件のみ（類似ケースで補完）"
        else:
            # 新規ポジションの場合
            overall_matches = search_results.get("overall_similarity", [])
            if len(overall_matches) < 5:
                return False, "新規ポジションかつ類似ケースも少ないためRAGスキップ"
            else:
                return True, f"新規ポジションだが類似ケース{len(overall_matches)}件を参考に"
    
    def format_search_results_for_llm(self, search_results: Dict, use_rag: bool) -> Dict:
        """
        検索結果をLLM用にフォーマット
        """
        if not use_rag:
            return {
                "use_rag": False,
                "message": "参照データが不足しているため、通常の評価を実行します"
            }
        
        formatted = {
            "use_rag": True,
            "exact_position_matches": [],
            "similar_cases": [],
            "success_patterns": []
        }
        
        # ポジション完全一致
        for match in search_results.get("exact_position_match", [])[:5]:
            formatted["exact_position_matches"].append({
                "case_id": match["metadata"]["case_id"],
                "similarity": match["score"],
                "ai_recommendation": match["metadata"]["ai_recommendation"],
                "client_recommendation": match["metadata"]["client_recommendation"],
                "match": match["metadata"]["match"]
            })
        
        # 類似ケース（ポジション問わず）
        for match in search_results.get("overall_similarity", [])[:10]:
            if match["metadata"]["position"] != search_results.get("current_position"):
                formatted["similar_cases"].append({
                    "case_id": match["metadata"]["case_id"],
                    "position": match["metadata"]["position"],
                    "similarity": match["score"],
                    "ai_recommendation": match["metadata"]["ai_recommendation"],
                    "client_recommendation": match["metadata"]["client_recommendation"]
                })
        
        # 成功パターン
        for match in search_results.get("success_patterns", [])[:3]:
            formatted["success_patterns"].append({
                "case_id": match["metadata"]["case_id"],
                "position": match["metadata"]["position"],
                "similarity": match["score"],
                "pattern": "高評価事例"
            })
        
        return formatted