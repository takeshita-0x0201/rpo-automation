"""
ベクトルDB管理用エンドポイント
手動同期と統計情報の確認
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict
import logging

from .auth import get_current_user
from webapp.services.vector_sync_orchestrator import vector_sync_orchestrator
from webapp.services.pinecone_service import pinecone_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/vector", tags=["vector_admin"])

@router.post("/sync/manual")
async def manual_sync(
    limit: int = 5,
    user: dict = Depends(get_current_user)
) -> Dict:
    """
    手動でベクトル同期を実行
    
    Args:
        limit: 処理する評価の最大数（デフォルト: 5）
    """
    if user.get("role") not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="権限がありません")
    
    try:
        # 同期を実行
        results = await vector_sync_orchestrator.sync_batch(limit=limit)
        return results
        
    except Exception as e:
        logger.error(f"Manual sync error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_vector_stats(
    user: dict = Depends(get_current_user)
) -> Dict:
    """
    ベクトルDBの統計情報を取得
    """
    if user.get("role") not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="権限がありません")
    
    try:
        # Pineconeの統計情報
        pinecone_stats = pinecone_service.get_index_stats()
        
        # Gemini Embeddingのクォータ情報
        from webapp.services.embedding_service import embedding_service
        embedding_quota = embedding_service.get_remaining_quota()
        
        return {
            "pinecone": pinecone_stats,
            "embedding_quota": embedding_quota
        }
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sync/test")
async def test_sync_single(
    candidate_id: str,
    requirement_id: str,
    user: dict = Depends(get_current_user)
) -> Dict:
    """
    特定の評価を手動で同期（テスト用）
    """
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="管理者権限が必要です")
    
    try:
        from core.utils.supabase_client import get_supabase_client
        supabase = get_supabase_client()
        
        # 評価を取得
        response = supabase.table('client_evaluations')\
            .select('*')\
            .eq('candidate_id', candidate_id)\
            .eq('requirement_id', requirement_id)\
            .single()\
            .execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="評価が見つかりません")
        
        evaluation = response.data
        
        # 単一評価を処理
        success = await vector_sync_orchestrator._process_single_evaluation(evaluation)
        
        return {
            "success": success,
            "evaluation": evaluation
        }
        
    except Exception as e:
        logger.error(f"Test sync error: {e}")
        raise HTTPException(status_code=500, detail=str(e))