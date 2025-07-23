"""
クライアント評価APIエンドポイント
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from routers.auth import get_current_user
from core.utils.supabase_client import get_supabase_client

router = APIRouter(prefix="/api/evaluations", tags=["evaluations"])

class ClientFeedbackRequest(BaseModel):
    """クライアント評価リクエスト"""
    client_evaluation: str  # A, B, C, D
    client_comment: Optional[str] = None

@router.patch("/{evaluation_id}/client-feedback")
async def update_client_feedback(
    evaluation_id: str,
    feedback: ClientFeedbackRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    クライアント評価を更新
    
    Args:
        evaluation_id: 評価ID
        feedback: クライアントからのフィードバック
        current_user: 現在のユーザー
    
    Returns:
        更新された評価データ
    """
    # 権限チェック（adminまたはmanagerのみ）
    if current_user.get("role") not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # 評価値のバリデーション
    if feedback.client_evaluation not in ["A", "B", "C", "D"]:
        raise HTTPException(
            status_code=400, 
            detail="Invalid client_evaluation. Must be A, B, C, or D"
        )
    
    supabase = get_supabase_client()
    
    try:
        # 評価の存在確認
        eval_response = supabase.table('ai_evaluations')\
            .select("*")\
            .eq('id', evaluation_id)\
            .single()\
            .execute()
        
        if not eval_response.data:
            raise HTTPException(status_code=404, detail="Evaluation not found")
        
        # クライアント評価を更新
        update_data = {
            "client_evaluation": feedback.client_evaluation,
            "client_comment": feedback.client_comment,
            "updated_at": datetime.utcnow().isoformat(),
            "synced_to_pinecone": False  # 同期フラグをリセット
        }
        
        update_response = supabase.table('ai_evaluations')\
            .update(update_data)\
            .eq('id', evaluation_id)\
            .execute()
        
        return {
            "success": True,
            "data": update_response.data[0] if update_response.data else None
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{evaluation_id}")
async def get_evaluation(
    evaluation_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    評価詳細を取得
    
    Args:
        evaluation_id: 評価ID
        current_user: 現在のユーザー
    
    Returns:
        評価データ（関連する候補者・要件情報を含む）
    """
    supabase = get_supabase_client()
    
    try:
        # 評価データを関連情報と共に取得
        response = supabase.table('ai_evaluations')\
            .select("""
                *,
                candidate:candidates(*),
                requirement:job_requirements(*, client:clients(*))
            """)\
            .eq('id', evaluation_id)\
            .single()\
            .execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Evaluation not found")
        
        return response.data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/")
async def list_evaluations(
    job_id: Optional[str] = None,
    requirement_id: Optional[str] = None,
    include_client_feedback: bool = False,
    current_user: dict = Depends(get_current_user)
):
    """
    評価一覧を取得
    
    Args:
        job_id: ジョブIDでフィルタ
        requirement_id: 要件IDでフィルタ
        include_client_feedback: クライアントフィードバックがあるもののみ
        current_user: 現在のユーザー
    
    Returns:
        評価データのリスト
    """
    supabase = get_supabase_client()
    
    try:
        query = supabase.table('ai_evaluations')\
            .select("""
                *,
                candidate:candidates(candidate_company, candidate_id),
                requirement:job_requirements(title)
            """)
        
        # フィルタ条件を追加
        if job_id:
            query = query.eq('job_id', job_id)
        if requirement_id:
            query = query.eq('requirement_id', requirement_id)
        if include_client_feedback:
            query = query.not_.is_('client_evaluation', 'null')
        
        # 作成日時の降順でソート
        query = query.order('created_at', desc=True)
        
        response = query.execute()
        
        return response.data if response.data else []
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))