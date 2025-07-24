"""
動的な検索戦略ノード
評価結果とギャップ分析に基づいて、検索戦略を動的に調整する
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import re

from .base import BaseNode, ResearchState, EvaluationResult, InformationGap


@dataclass
class SearchStrategy:
    """検索戦略"""
    priority_gaps: List[InformationGap]  # 優先度の高いギャップ
    search_depth: str  # 検索深度: "shallow", "medium", "deep"
    search_focus: List[str]  # 検索フォーカス領域
    max_searches: int  # 最大検索数
    confidence_threshold: float  # 確信度閾値


class AdaptiveSearchStrategyNode(BaseNode):
    """動的検索戦略ノード"""
    
    def __init__(self):
        super().__init__("AdaptiveSearchStrategy")
        
        # 戦略パラメータ
        self.confidence_thresholds = {
            "高": 0.85,
            "中": 0.70,
            "低": 0.50
        }
        
        # スコア範囲に基づく戦略
        self.score_strategies = {
            "high": {  # 80点以上
                "search_depth": "shallow",
                "max_searches": 1,
                "focus": ["validation", "recent_updates"]
            },
            "medium": {  # 60-79点
                "search_depth": "medium",
                "max_searches": 2,
                "focus": ["missing_requirements", "experience_details"]
            },
            "low": {  # 60点未満
                "search_depth": "deep",
                "max_searches": 3,
                "focus": ["alternative_evidence", "related_experience", "transferable_skills"]
            }
        }
    
    async def process(self, state: ResearchState) -> ResearchState:
        """評価結果に基づいて検索戦略を決定"""
        self.state = "processing"
        
        if not state.current_evaluation:
            print("  [AdaptiveStrategy] 評価結果がないため、デフォルト戦略を使用")
            return state
        
        # 現在の評価状態を分析
        strategy = self._analyze_and_decide_strategy(state)
        
        # 戦略に基づいてギャップを調整
        adjusted_gaps = self._adjust_gaps_by_strategy(state.information_gaps, strategy)
        
        # 更新されたギャップをstateに反映
        state.information_gaps = adjusted_gaps
        
        print(f"  [AdaptiveStrategy] 戦略決定:")
        print(f"    - 検索深度: {strategy.search_depth}")
        print(f"    - 最大検索数: {strategy.max_searches}")
        print(f"    - フォーカス領域: {', '.join(strategy.search_focus)}")
        print(f"    - 調整後のギャップ数: {len(adjusted_gaps)}")
        
        self.state = "completed"
        return state
    
    def _analyze_and_decide_strategy(self, state: ResearchState) -> SearchStrategy:
        """評価結果を分析して戦略を決定"""
        evaluation = state.current_evaluation
        score = evaluation.score
        confidence = evaluation.confidence
        
        # スコアに基づく基本戦略を決定
        if score >= 80:
            base_strategy = self.score_strategies["high"]
        elif score >= 60:
            base_strategy = self.score_strategies["medium"]
        else:
            base_strategy = self.score_strategies["low"]
        
        # 確信度による調整
        confidence_value = self.confidence_thresholds.get(confidence, 0.5)
        
        # 懸念点の分析
        critical_concerns = self._analyze_concerns(evaluation.concerns)
        
        # フォーカス領域の決定
        focus_areas = list(base_strategy["focus"])
        
        # 必須要件不足の場合は追加調査
        if self._has_missing_requirements(evaluation):
            focus_areas.append("requirement_validation")
            if "deep" not in base_strategy["search_depth"]:
                base_strategy["search_depth"] = "medium"
        
        # 企業規模ミスマッチの場合
        if self._has_company_size_mismatch(evaluation):
            focus_areas.append("company_culture_fit")
        
        # 最大検索数の調整（確信度が低い場合は増やす）
        max_searches = base_strategy["max_searches"]
        if confidence_value < 0.7:
            max_searches = min(max_searches + 1, 4)
        
        return SearchStrategy(
            priority_gaps=[],  # 後で設定
            search_depth=base_strategy["search_depth"],
            search_focus=focus_areas,
            max_searches=max_searches,
            confidence_threshold=confidence_value
        )
    
    def _analyze_concerns(self, concerns: List[str]) -> Dict[str, int]:
        """懸念点を分析してカテゴリ別に集計"""
        concern_categories = {
            "missing_requirements": 0,
            "experience_gap": 0,
            "technical_skills": 0,
            "company_fit": 0,
            "other": 0
        }
        
        for concern in concerns:
            if "必須要件" in concern or "要件を満たして" in concern:
                concern_categories["missing_requirements"] += 1
            elif "経験が" in concern or "実績が" in concern:
                concern_categories["experience_gap"] += 1
            elif "技術" in concern or "スキル" in concern:
                concern_categories["technical_skills"] += 1
            elif "企業規模" in concern or "文化" in concern:
                concern_categories["company_fit"] += 1
            else:
                concern_categories["other"] += 1
        
        return concern_categories
    
    def _has_missing_requirements(self, evaluation: EvaluationResult) -> bool:
        """必須要件不足があるかチェック"""
        # 懸念点に必須要件関連の記述があるか
        for concern in evaluation.concerns:
            if "必須要件" in concern and ("満たして" in concern or "不足" in concern or "欠如" in concern):
                return True
        
        # スコアが低く、サマリーに必須要件の記述がある場合
        if evaluation.score < 70 and "必須要件" in evaluation.summary:
            return True
        
        return False
    
    def _has_company_size_mismatch(self, evaluation: EvaluationResult) -> bool:
        """企業規模のミスマッチがあるかチェック"""
        for concern in evaluation.concerns:
            if "企業規模" in concern or "規模差" in concern:
                return True
        return False
    
    def _adjust_gaps_by_strategy(self, gaps: List[InformationGap], strategy: SearchStrategy) -> List[InformationGap]:
        """戦略に基づいてギャップを調整"""
        if not gaps:
            return []
        
        # フォーカス領域に基づいてギャップをフィルタリング・優先順位付け
        priority_gaps = []
        other_gaps = []
        
        for gap in gaps:
            # フォーカス領域に関連するギャップを優先
            is_priority = False
            
            for focus in strategy.search_focus:
                if focus == "validation" and "確認" in gap.description:
                    is_priority = True
                elif focus == "recent_updates" and ("最新" in gap.description or "現在" in gap.description):
                    is_priority = True
                elif focus == "missing_requirements" and "要件" in gap.info_type:
                    is_priority = True
                elif focus == "experience_details" and "経験" in gap.info_type:
                    is_priority = True
                elif focus == "company_culture_fit" and ("企業" in gap.info_type or "文化" in gap.info_type):
                    is_priority = True
                elif focus == "alternative_evidence" and "代替" in gap.description:
                    is_priority = True
                elif focus == "transferable_skills" and "スキル" in gap.info_type:
                    is_priority = True
            
            if is_priority:
                priority_gaps.append(gap)
            else:
                other_gaps.append(gap)
        
        # 重要度でソート
        priority_gaps.sort(key=lambda x: {"高": 3, "中": 2, "低": 1}.get(x.importance, 0), reverse=True)
        other_gaps.sort(key=lambda x: {"高": 3, "中": 2, "低": 1}.get(x.importance, 0), reverse=True)
        
        # 戦略の最大検索数に基づいて制限
        all_gaps = priority_gaps + other_gaps
        adjusted_gaps = all_gaps[:strategy.max_searches]
        
        # 検索深度に基づいてクエリを調整
        for gap in adjusted_gaps:
            gap.search_query = self._adjust_query_by_depth(gap.search_query, strategy.search_depth)
        
        return adjusted_gaps
    
    def _adjust_query_by_depth(self, query: str, depth: str) -> str:
        """検索深度に基づいてクエリを調整"""
        if depth == "shallow":
            # 基本的な検索（現在の情報のみ）
            if "経験" not in query:
                query += " 最新"
        elif depth == "medium":
            # 中程度の検索（関連情報も含む）
            if "または" not in query:
                query += " 関連"
        elif depth == "deep":
            # 深い検索（代替情報や類似経験も含む）
            if "類似" not in query and "代替" not in query:
                query += " 類似 OR 代替 OR 関連"
        
        return query