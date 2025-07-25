"""
モジュール化された評価オーケストレーター
複数の専門ノードを使用して候補者を評価
"""

from typing import Dict, Optional, List
import asyncio

from .base import BaseNode, ResearchState, EvaluationResult
from .skill_evaluator import SkillEvaluatorNode
from .experience_evaluator import ExperienceEvaluatorNode
from .fit_evaluator import FitEvaluatorNode
from .final_scorer import FinalScorerNode


class ModularEvaluatorNode(BaseNode):
    """複数の専門ノードを統合して評価を行うオーケストレーター"""
    
    def __init__(self, api_key: str, supabase_url: Optional[str] = None, supabase_key: Optional[str] = None):
        super().__init__("ModularEvaluator")
        
        # 各専門ノードの初期化
        self.skill_evaluator = SkillEvaluatorNode(api_key)
        self.experience_evaluator = ExperienceEvaluatorNode(api_key)
        self.fit_evaluator = FitEvaluatorNode(api_key)
        self.final_scorer = FinalScorerNode(api_key)
        
        # Supabase設定（元のEvaluatorNodeとの互換性のため保持）
        self.supabase_url = supabase_url
        self.supabase_key = supabase_key
    
    async def process(self, state: ResearchState) -> ResearchState:
        """モジュール化された評価プロセスを実行"""
        self.state = "processing"
        
        print(f"\n=== モジュール評価開始（サイクル{state.current_cycle}） ===")
        
        try:
            # 並列実行可能な評価を同時実行
            print("  並列評価フェーズを開始...")
            
            # スキル評価と実務経験評価を並列実行
            skill_task = asyncio.create_task(self.skill_evaluator.process(state))
            experience_task = asyncio.create_task(self.experience_evaluator.process(state))
            
            # 並列実行の完了を待つ
            await asyncio.gather(skill_task, experience_task)
            
            # 状態を更新（並列実行の結果をマージ）
            state = await self._merge_states([skill_task.result(), experience_task.result()], state)
            
            print("  組織適合性評価を開始...")
            # 組織適合性評価（前の評価結果を参照する可能性があるため順次実行）
            state = await self.fit_evaluator.process(state)
            
            print("  最終スコア統合を開始...")
            # 最終スコア統合
            state = await self.final_scorer.process(state)
            
            print(f"\n=== モジュール評価完了 ===")
            print(f"  最終スコア: {state.current_evaluation.score}")
            print(f"  確信度: {state.current_evaluation.confidence}")
            
            self.state = "completed"
            return state
            
        except Exception as e:
            print(f"  エラーが発生しました: {str(e)}")
            self.state = "failed"
            raise
    
    async def _merge_states(self, states: List[ResearchState], original_state: ResearchState) -> ResearchState:
        """並列実行された状態をマージ"""
        # partial_scoresをマージ
        merged_partial_scores = {}
        
        for state in states:
            if hasattr(state, 'partial_scores'):
                merged_partial_scores.update(state.partial_scores)
        
        # 元の状態に部分スコアを設定
        original_state.partial_scores = merged_partial_scores
        
        return original_state
    
    def get_evaluation_summary(self, state: ResearchState) -> Dict:
        """評価結果のサマリーを取得"""
        if not hasattr(state, 'current_evaluation') or not state.current_evaluation:
            return {"error": "評価が完了していません"}
        
        eval_result = state.current_evaluation
        
        # スコア内訳の詳細を整形
        score_details = {}
        if hasattr(eval_result, 'score_breakdown'):
            for category, detail in eval_result.score_breakdown.items():
                score_details[category] = {
                    "score": detail.actual_score,
                    "max_score": detail.max_score,
                    "percentage": round((detail.actual_score / detail.max_score) * 100) if detail.max_score > 0 else 0
                }
        
        return {
            "final_score": eval_result.score,
            "confidence": eval_result.confidence,
            "score_breakdown": score_details,
            "strengths": eval_result.strengths,
            "concerns": eval_result.concerns,
            "summary": eval_result.summary,
            "evaluation_cycle": state.current_cycle
        }