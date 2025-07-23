"""
クライアント評価管理ルーター
スプレッドシートからのバッチアップロードとベクトルDB連携
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import logging

from core.utils.supabase_client import get_supabase_client
from .auth import get_current_user, get_api_key_user

logger = logging.getLogger(__name__)

router = APIRouter()

# リクエストモデル
class ClientEvaluation(BaseModel):
    row_number: int
    candidate_name: str
    candidate_company: str
    candidate_link: str
    assigned_hm: str
    judgement: str
    note: Optional[str] = ""
    client_name: str
    job_title: str
    evaluation_date: str

class BatchUploadRequest(BaseModel):
    evaluations: List[ClientEvaluation]
    source: str = "google_sheets"
    uploaded_at: str

# レスポンスモデル
class BatchUploadResponse(BaseModel):
    success: bool
    processed: int
    failed: int
    errors: List[dict] = []

@router.post("/batch-upload", response_model=BatchUploadResponse)
async def batch_upload_evaluations(
    request: BatchUploadRequest,
    user: dict = Depends(get_api_key_user)  # API Key認証
):
    """
    スプレッドシートからのクライアント評価バッチアップロード
    
    1. candidate_nameとjob_titleからIDを解決
    2. client_evaluationsテーブルに保存
    3. バックグラウンドでベクトルDB処理を開始
    """
    try:
        supabase = get_supabase_client()
        processed = 0
        failed = 0
        errors = []
        
        for eval_data in request.evaluations:
            try:
                # 1. candidate_idの解決（candidate_nameから検索）
                candidates_response = supabase.table('candidates').select('id').eq('candidate_id', eval_data.candidate_name).execute()
                
                if not candidates_response.data:
                    # 候補者名で再検索（candidate_idフィールドが実際は名前を含んでいる）
                    errors.append({
                        "row": eval_data.row_number,
                        "error": f"候補者 '{eval_data.candidate_name}' が見つかりません"
                    })
                    failed += 1
                    continue
                
                candidate_id = candidates_response.data[0]['id']
                
                # 2. requirement_idの解決（client_nameとjob_titleから検索）
                requirements_response = supabase.table('job_requirements').select('id, requirement_id').eq('title', eval_data.job_title).execute()
                
                if not requirements_response.data:
                    errors.append({
                        "row": eval_data.row_number,
                        "error": f"求人 '{eval_data.job_title}' が見つかりません"
                    })
                    failed += 1
                    continue
                
                # requirement_idはTEXT型
                requirement_id = requirements_response.data[0]['requirement_id'] or requirements_response.data[0]['id']
                
                # 3. 既存の評価があるか確認
                existing_response = supabase.table('client_evaluations').select('*').eq('candidate_id', eval_data.candidate_name).eq('requirement_id', requirement_id).execute()
                
                # 4. client_evaluationsテーブルに保存/更新
                evaluation_data = {
                    'candidate_id': eval_data.candidate_name,  # TEXT型なので名前をそのまま使用
                    'requirement_id': str(requirement_id),
                    'client_evaluation': eval_data.judgement,
                    'client_feedback': eval_data.note,
                    'evaluation_date': datetime.fromisoformat(eval_data.evaluation_date.replace('Z', '+00:00')).date().isoformat(),
                    'created_by': eval_data.assigned_hm,
                    'updated_at': datetime.now().isoformat()
                }
                
                if existing_response.data:
                    # 更新
                    supabase.table('client_evaluations').update(evaluation_data).eq('candidate_id', eval_data.candidate_name).eq('requirement_id', requirement_id).execute()
                else:
                    # 新規作成
                    evaluation_data['created_at'] = datetime.now().isoformat()
                    evaluation_data['synced_to_pinecone'] = False
                    evaluation_data['sync_retry_count'] = 0
                    supabase.table('client_evaluations').insert(evaluation_data).execute()
                
                processed += 1
                
            except Exception as e:
                logger.error(f"Error processing row {eval_data.row_number}: {str(e)}")
                errors.append({
                    "row": eval_data.row_number,
                    "error": str(e)
                })
                failed += 1
        
        # 5. ベクトルDB同期はEdge Functionで1時間ごとに実行される
        # (Supabase cron jobで設定済み)
        
        return BatchUploadResponse(
            success=True,
            processed=processed,
            failed=failed,
            errors=errors
        )
        
    except Exception as e:
        logger.error(f"Batch upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# trigger_vector_sync関数は削除されました
# ベクトルDB同期はSupabase Edge Functionで実行されます

@router.get("/sync-status")
async def get_sync_status(
    user: dict = Depends(get_current_user)
):
    """
    ベクトルDB同期状態を取得
    """
    try:
        supabase = get_supabase_client()
        
        # 同期待ちの件数を取得
        pending_response = supabase.table('client_evaluations').select('count', count='exact').eq('synced_to_pinecone', False).execute()
        
        # エラー件数を取得
        error_response = supabase.table('client_evaluations').select('count', count='exact').neq('sync_error', None).execute()
        
        # 同期済み件数を取得
        synced_response = supabase.table('client_evaluations').select('count', count='exact').eq('synced_to_pinecone', True).execute()
        
        return {
            "pending": pending_response.count or 0,
            "errors": error_response.count or 0,
            "synced": synced_response.count or 0,
            "total": (pending_response.count or 0) + (synced_response.count or 0)
        }
        
    except Exception as e:
        logger.error(f"Error getting sync status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))