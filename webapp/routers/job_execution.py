"""
ジョブ実行管理エンドポイント
AIマッチングジョブの実行を管理
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import Optional

from webapp.dependencies import authenticated_user
from webapp.services.ai_matching_service import ai_matching_service
from core.utils.supabase_client import get_supabase_client

router = APIRouter(prefix="/api/jobs", tags=["job-execution"])

@router.post("/{job_id}/execute")
async def execute_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(authenticated_user)
):
    """ジョブを実行"""
    try:
        supabase = get_supabase_client()
        
        # ジョブの存在と権限確認
        job_response = supabase.table('jobs').select('*, client:clients(*)').eq('id', job_id).single().execute()
        
        if not job_response.data:
            raise HTTPException(status_code=404, detail="ジョブが見つかりません")
        
        job = job_response.data
        
        # 権限チェック（管理者またはジョブ作成者）
        if current_user['role'] != 'admin' and job.get('created_by') != current_user['id']:
            raise HTTPException(status_code=403, detail="このジョブを実行する権限がありません")
        
        # ジョブタイプの確認
        if job.get('job_type') != 'ai_matching':
            raise HTTPException(status_code=400, detail="AIマッチングジョブではありません")
        
        # ステータスの確認
        if job.get('status') not in ['pending', 'failed']:
            raise HTTPException(status_code=400, detail="このジョブは既に実行中または完了しています")
        
        # バックグラウンドでジョブを実行
        background_tasks.add_task(
            ai_matching_service.process_job,
            job_id
        )
        
        return {
            "success": True,
            "message": "ジョブの実行を開始しました",
            "job_id": job_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ジョブの実行開始に失敗しました: {str(e)}")

@router.get("/{job_id}/status")
async def get_job_status(
    job_id: str,
    current_user: dict = Depends(authenticated_user)
):
    """ジョブのステータスを取得"""
    try:
        supabase = get_supabase_client()
        
        # ジョブ情報を取得
        job_response = supabase.table('jobs').select('id, status, progress, created_at, started_at, completed_at, error_message').eq('id', job_id).single().execute()
        
        if not job_response.data:
            raise HTTPException(status_code=404, detail="ジョブが見つかりません")
        
        job = job_response.data
        
        # 評価済み候補者数を取得
        if job['status'] in ['running', 'completed']:
            eval_count_response = supabase.table('ai_evaluations').select('id', count='exact').eq('search_id', job_id).execute()
            job['evaluated_count'] = eval_count_response.count or 0
        else:
            job['evaluated_count'] = 0
        
        return job
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ステータスの取得に失敗しました: {str(e)}")

@router.post("/{job_id}/cancel")
async def cancel_job(
    job_id: str,
    current_user: dict = Depends(authenticated_user)
):
    """ジョブをキャンセル"""
    try:
        supabase = get_supabase_client()
        
        # ジョブの存在と権限確認
        job_response = supabase.table('jobs').select('*').eq('id', job_id).single().execute()
        
        if not job_response.data:
            raise HTTPException(status_code=404, detail="ジョブが見つかりません")
        
        job = job_response.data
        
        # 権限チェック
        if current_user['role'] != 'admin' and job.get('created_by') != current_user['id']:
            raise HTTPException(status_code=403, detail="このジョブをキャンセルする権限がありません")
        
        # ステータスの確認
        if job.get('status') not in ['pending', 'running']:
            raise HTTPException(status_code=400, detail="このジョブはキャンセルできません")
        
        # ジョブをキャンセル
        update_response = supabase.table('jobs').update({
            'status': 'cancelled',
            'completed_at': 'now()'
        }).eq('id', job_id).execute()
        
        return {
            "success": True,
            "message": "ジョブをキャンセルしました"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"キャンセルに失敗しました: {str(e)}")