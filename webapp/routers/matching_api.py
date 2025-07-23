"""
AIマッチング用APIエンドポイント
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import uuid
import httpx
import os

from core.utils.supabase_client import get_supabase_client
from dependencies import get_current_user

router = APIRouter(prefix="/api/matching", tags=["matching"])

# リクエスト/レスポンスモデル
class StartMatchingRequest(BaseModel):
    requirement_id: str
    candidate_ids: List[str]

class StartMatchingResponse(BaseModel):
    job_ids: List[str]
    message: str

class JobStatusResponse(BaseModel):
    id: str
    requirement_id: str
    candidate_id: str
    status: str
    progress: int
    current_stage: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    result: Optional[dict]
    error_message: Optional[str]

class MatchingResultResponse(BaseModel):
    job_id: str
    final_score: int
    recommendation: str
    confidence: str
    strengths: List[str]
    concerns: List[str]
    interview_points: List[str]
    overall_assessment: Optional[str]

# エンドポイント実装

@router.post("/start", response_model=StartMatchingResponse)
async def start_matching(
    request: StartMatchingRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """AIマッチングジョブを開始"""
    try:
        supabase = get_supabase_client()
        job_ids = []
        
        # 要件の存在確認
        requirement = supabase.table('job_requirements').select('id, title').eq('id', request.requirement_id).single().execute()
        if not requirement.data:
            raise HTTPException(status_code=404, detail="指定された要件が見つかりません")
        
        # 各候補者に対してジョブを作成
        for candidate_id in request.candidate_ids:
            # 候補者の存在確認
            candidate = supabase.table('candidates').select('id, candidate_id').eq('id', candidate_id).single().execute()
            if not candidate.data:
                continue
            
            # ジョブレコードを作成
            job_data = {
                'requirement_id': request.requirement_id,
                'candidate_id': candidate_id,
                'user_id': current_user['id'],
                'status': 'pending',
                'progress': 0,
                'max_cycles': 3
            }
            
            job_result = supabase.table('matching_jobs').insert(job_data).execute()
            if job_result.data:
                job_id = job_result.data[0]['id']
                job_ids.append(job_id)
                
                # Edge Function を非同期で呼び出し
                background_tasks.add_task(
                    trigger_edge_function,
                    job_id,
                    request.requirement_id,
                    candidate_id
                )
        
        if not job_ids:
            raise HTTPException(status_code=400, detail="処理可能な候補者が見つかりません")
        
        return StartMatchingResponse(
            job_ids=job_ids,
            message=f"{len(job_ids)}件のマッチング処理を開始しました"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ジョブの開始に失敗しました: {str(e)}")

@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """ジョブの状態を取得"""
    try:
        supabase = get_supabase_client()
        
        # ジョブ情報を取得（ユーザー権限チェック込み）
        result = supabase.table('matching_jobs')\
            .select('*')\
            .eq('id', job_id)\
            .eq('user_id', current_user['id'])\
            .single()\
            .execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="ジョブが見つかりません")
        
        return JobStatusResponse(**result.data)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ジョブ情報の取得に失敗しました: {str(e)}")

@router.get("/jobs/{job_id}/result", response_model=MatchingResultResponse)
async def get_matching_result(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """マッチング結果を取得"""
    try:
        supabase = get_supabase_client()
        
        # ジョブの完了確認
        job = supabase.table('matching_jobs')\
            .select('status, result')\
            .eq('id', job_id)\
            .eq('user_id', current_user['id'])\
            .single()\
            .execute()
        
        if not job.data:
            raise HTTPException(status_code=404, detail="ジョブが見つかりません")
        
        if job.data['status'] != 'completed':
            raise HTTPException(status_code=400, detail="ジョブがまだ完了していません")
        
        # 詳細結果を取得
        result = supabase.table('matching_results')\
            .select('*')\
            .eq('job_id', job_id)\
            .single()\
            .execute()
        
        if not result.data:
            # 簡易結果から返す
            job_result = job.data.get('result', {})
            return MatchingResultResponse(
                job_id=job_id,
                final_score=job_result.get('final_score', 0),
                recommendation=job_result.get('recommendation', 'D'),
                confidence=job_result.get('confidence', 'Low'),
                strengths=job_result.get('strengths', []),
                concerns=job_result.get('concerns', []),
                interview_points=job_result.get('interview_points', []),
                overall_assessment=job_result.get('overall_assessment')
            )
        
        return MatchingResultResponse(**result.data)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"結果の取得に失敗しました: {str(e)}")

@router.get("/jobs", response_model=List[JobStatusResponse])
async def list_jobs(
    requirement_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    current_user: dict = Depends(get_current_user)
):
    """ジョブ一覧を取得"""
    try:
        supabase = get_supabase_client()
        
        query = supabase.table('matching_jobs')\
            .select('*')\
            .eq('user_id', current_user['id'])\
            .order('created_at', desc=True)\
            .limit(limit)\
            .offset(offset)
        
        if requirement_id:
            query = query.eq('requirement_id', requirement_id)
        
        if status:
            query = query.eq('status', status)
        
        result = query.execute()
        
        return [JobStatusResponse(**job) for job in result.data]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ジョブ一覧の取得に失敗しました: {str(e)}")

@router.post("/jobs/{job_id}/cancel")
async def cancel_job(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """ジョブをキャンセル"""
    try:
        supabase = get_supabase_client()
        
        # ジョブの状態を確認
        job = supabase.table('matching_jobs')\
            .select('status')\
            .eq('id', job_id)\
            .eq('user_id', current_user['id'])\
            .single()\
            .execute()
        
        if not job.data:
            raise HTTPException(status_code=404, detail="ジョブが見つかりません")
        
        if job.data['status'] in ['completed', 'failed', 'cancelled']:
            raise HTTPException(status_code=400, detail="すでに終了したジョブはキャンセルできません")
        
        # キャンセル処理
        update_result = supabase.table('matching_jobs')\
            .update({
                'status': 'cancelled',
                'completed_at': datetime.utcnow().isoformat()
            })\
            .eq('id', job_id)\
            .execute()
        
        return {"message": "ジョブをキャンセルしました"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"キャンセルに失敗しました: {str(e)}")

# Edge Function を呼び出す関数
async def trigger_edge_function(job_id: str, requirement_id: str, candidate_id: str):
    """Edge Function を非同期で呼び出し"""
    try:
        # Supabase Edge Function のURL
        edge_function_url = f"{os.getenv('SUPABASE_URL')}/functions/v1/process-matching"
        
        # サービスロールキーを使用
        headers = {
            "Authorization": f"Bearer {os.getenv('SUPABASE_SERVICE_ROLE_KEY')}",
            "Content-Type": "application/json"
        }
        
        # リクエストボディ
        data = {
            "jobId": job_id,
            "requirementId": requirement_id,
            "candidateId": candidate_id
        }
        
        # Edge Function を呼び出し
        async with httpx.AsyncClient() as client:
            response = await client.post(
                edge_function_url,
                headers=headers,
                json=data,
                timeout=60.0  # 60秒のタイムアウト
            )
            
            if response.status_code != 200:
                print(f"Edge Function call failed: {response.status_code} - {response.text}")
                # エラーをDBに記録
                supabase = get_supabase_client()
                supabase.table('matching_jobs').update({
                    'status': 'failed',
                    'error_message': f"Edge Function error: {response.status_code}",
                    'completed_at': datetime.utcnow().isoformat()
                }).eq('id', job_id).execute()
                
    except Exception as e:
        print(f"Failed to trigger Edge Function: {str(e)}")
        # エラーをDBに記録
        try:
            supabase = get_supabase_client()
            supabase.table('matching_jobs').update({
                'status': 'failed',
                'error_message': str(e),
                'completed_at': datetime.utcnow().isoformat()
            }).eq('id', job_id).execute()
        except:
            pass