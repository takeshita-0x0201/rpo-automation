"""
フィードバック収集API
クライアントやリクルーターからの評価フィードバックを受け付ける
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime
import sys
import os

# ai_matching_systemをインポートパスに追加
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
ai_matching_path = os.path.join(project_root, "ai_matching_system")
sys.path.append(ai_matching_path)

try:
    from ai_matching.utils.feedback_collector import get_feedback_collector, FeedbackType
    from ai_matching.utils.ab_testing import get_ab_testing_framework
except ImportError:
    print("Warning: AI matching system not available for feedback collection")
    get_feedback_collector = None
    get_ab_testing_framework = None

from .auth import get_current_user

router = APIRouter()


class FeedbackRequest(BaseModel):
    """フィードバックリクエスト"""
    candidate_id: str
    job_id: str
    feedback_type: str
    feedback_text: str
    original_score: int
    suggested_score: Optional[int] = None
    tags: Optional[List[str]] = None


class ScoreCorrectionRequest(BaseModel):
    """スコア修正リクエスト"""
    feedback_id: int
    original_evaluation_id: int
    reason_category: str
    correction_details: str
    impact_analysis: Optional[str] = None


@router.post("/feedback")
async def submit_feedback(
    request: FeedbackRequest,
    current_user: dict = Depends(get_current_user)
):
    """フィードバックを送信"""
    if not get_feedback_collector:
        raise HTTPException(status_code=503, detail="Feedback system not available")
    
    try:
        feedback_type_enum = FeedbackType(request.feedback_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid feedback type: {request.feedback_type}")
    
    collector = get_feedback_collector()
    
    # フィードバックを収集
    feedback_id = collector.collect_feedback(
        candidate_id=request.candidate_id,
        job_id=request.job_id,
        feedback_type=feedback_type_enum,
        feedback_text=request.feedback_text,
        original_score=request.original_score,
        suggested_score=request.suggested_score,
        tags=request.tags,
        user_id=current_user.get("id", "anonymous")
    )
    
    return {
        "success": True,
        "feedback_id": feedback_id,
        "message": "フィードバックを受け付けました"
    }


@router.post("/feedback/score-correction")
async def submit_score_correction(
    request: ScoreCorrectionRequest,
    current_user: dict = Depends(get_current_user)
):
    """スコア修正の詳細を送信"""
    if not get_feedback_collector:
        raise HTTPException(status_code=503, detail="Feedback system not available")
    
    collector = get_feedback_collector()
    
    # スコア修正を追加
    collector.add_score_correction(
        feedback_id=request.feedback_id,
        original_evaluation_id=request.original_evaluation_id,
        reason_category=request.reason_category,
        correction_details=request.correction_details,
        impact_analysis=request.impact_analysis
    )
    
    return {
        "success": True,
        "message": "スコア修正情報を記録しました"
    }


@router.get("/feedback/summary")
async def get_feedback_summary(
    days: int = 30,
    current_user: dict = Depends(get_current_user)
):
    """フィードバックサマリーを取得"""
    if not get_feedback_collector:
        raise HTTPException(status_code=503, detail="Feedback system not available")
    
    collector = get_feedback_collector()
    summary = collector.get_feedback_summary(days=days)
    
    return summary


@router.get("/feedback/candidate/{candidate_id}/job/{job_id}")
async def get_candidate_feedback(
    candidate_id: str,
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """特定の候補者のフィードバックを取得"""
    if not get_feedback_collector:
        raise HTTPException(status_code=503, detail="Feedback system not available")
    
    collector = get_feedback_collector()
    feedback_list = collector.get_candidate_feedback(candidate_id, job_id)
    
    return {
        "candidate_id": candidate_id,
        "job_id": job_id,
        "feedback": feedback_list
    }


@router.get("/feedback/insights")
async def get_improvement_insights(
    current_user: dict = Depends(get_current_user)
):
    """改善のための洞察を取得"""
    if not get_feedback_collector:
        raise HTTPException(status_code=503, detail="Feedback system not available")
    
    collector = get_feedback_collector()
    insights = collector.export_improvement_insights()
    
    return insights


# A/Bテスト関連のエンドポイント
@router.get("/experiments/active")
async def get_active_experiments(
    current_user: dict = Depends(get_current_user)
):
    """アクティブな実験を取得"""
    if not get_ab_testing_framework:
        raise HTTPException(status_code=503, detail="A/B testing not available")
    
    ab_testing = get_ab_testing_framework()
    return {
        "experiments": list(ab_testing.active_experiments.keys()),
        "count": len(ab_testing.active_experiments)
    }


@router.get("/experiments/{experiment_name}/results")
async def get_experiment_results(
    experiment_name: str,
    current_user: dict = Depends(get_current_user)
):
    """実験結果を取得"""
    if not get_ab_testing_framework:
        raise HTTPException(status_code=503, detail="A/B testing not available")
    
    ab_testing = get_ab_testing_framework()
    results = ab_testing.get_experiment_results(experiment_name)
    
    if not results:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    return results


@router.post("/experiments/create")
async def create_experiment(
    name: str,
    description: str,
    control_use_semantic: bool = False,
    variant_a_use_semantic: bool = True,
    current_user: dict = Depends(get_current_user)
):
    """新しい実験を作成"""
    if not get_ab_testing_framework:
        raise HTTPException(status_code=503, detail="A/B testing not available")
    
    ab_testing = get_ab_testing_framework()
    
    # 実験設定
    control_config = {
        "use_semantic_understanding": control_use_semantic,
        "approach": "rule_based"
    }
    
    variants = [
        {
            "name": "semantic_evaluation",
            "use_semantic_understanding": variant_a_use_semantic,
            "approach": "semantic_heavy"
        }
    ]
    
    experiment_id = ab_testing.create_experiment(
        name=name,
        description=description,
        control_config=control_config,
        variants=variants
    )
    
    return {
        "success": True,
        "experiment_id": experiment_id,
        "message": f"実験 '{name}' を作成しました"
    }