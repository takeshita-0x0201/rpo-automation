"""
Chrome拡張機能用のAPIエンドポイント
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from supabase import create_client

from core.utils.supabase_client import get_supabase_client
from webapp.middleware.extension_auth import get_extension_user

router = APIRouter(prefix="/api/extension", tags=["extension-api"])

class ClientResponse(BaseModel):
    id: str
    name: str
    industry: Optional[str] = None
    size: Optional[str] = None
    created_at: datetime

class RequirementResponse(BaseModel):
    id: str
    client_id: str
    title: str
    description: Optional[str] = None
    structured_data: Optional[dict] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    status: Optional[str] = None  # オプショナルに変更
    client: Optional[dict] = None  # For JOIN queries
    client_name: Optional[str] = None  # Added by the endpoint

class CandidateData(BaseModel):
    # 必須フィールド
    candidate_id: str
    candidate_link: str
    candidate_company: Optional[str] = None
    candidate_resume: Optional[str] = None
    
    # プラットフォーム情報
    platform: str = "bizreach"
    
    # リレーション情報
    client_id: str
    requirement_id: str
    scraping_session_id: str

class BatchCandidateRequest(BaseModel):
    candidates: List[CandidateData]
    session_id: str

@router.get("/clients", response_model=List[ClientResponse])
async def get_clients(
    current_user: dict = Depends(get_extension_user)
):
    """クライアント一覧を取得"""
    try:
        supabase = get_supabase_client()
        
        # ユーザーのロールに基づいてクライアントを取得
        if current_user["role"] == "admin":
            # 管理者は全てのクライアントを取得
            result = supabase.table('clients').select('*').order('name').execute()
        else:
            # 一般ユーザーはアクティブなクライアントのみ
            result = supabase.table('clients').select('*').eq('is_active', True).order('name').execute()
        
        return result.data
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="クライアント一覧の取得に失敗しました"
        )

@router.get("/requirements", response_model=List[RequirementResponse])
async def get_requirements(
    client_id: str = Query(..., description="クライアントID"),
    active_only: bool = Query(True, description="アクティブな要件のみ"),
    current_user: dict = Depends(get_extension_user)
):
    """指定クライアントの採用要件一覧を取得"""
    try:
        supabase = get_supabase_client()
        
        query = supabase.table('job_requirements').select('*').eq('client_id', client_id)
        
        if active_only:
            query = query.eq('is_active', True)
        
        result = query.order('created_at', desc=True).execute()
        
        return result.data
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="採用要件の取得に失敗しました"
        )

@router.get("/test")
async def test_connection(
    current_user: dict = Depends(get_extension_user)
):
    """接続テスト"""
    try:
        supabase = get_supabase_client()
        
        # テーブル一覧を取得してみる
        tables_info = {
            "user": current_user,
            "message": "Connection successful"
        }
        
        # job_requirementsテーブルの存在確認
        try:
            test_result = supabase.table('job_requirements').select('id').limit(1).execute()
            tables_info["job_requirements_exists"] = True
            tables_info["job_requirements_count"] = len(test_result.data) if test_result.data else 0
        except Exception as e:
            tables_info["job_requirements_exists"] = False
            tables_info["job_requirements_error"] = str(e)
        
        # scraping_sessionsテーブルの存在確認
        try:
            test_result = supabase.table('scraping_sessions').select('id').limit(1).execute()
            tables_info["scraping_sessions_exists"] = True
            tables_info["scraping_sessions_count"] = len(test_result.data) if test_result.data else 0
        except Exception as e:
            tables_info["scraping_sessions_exists"] = False
            tables_info["scraping_sessions_error"] = str(e)
        
        return tables_info
        
    except Exception as e:
        return {"error": str(e), "user": current_user}

@router.get("/requirements/all")
async def get_all_requirements(
    active_only: bool = Query(True, description="アクティブな要件のみ"),
    current_user: dict = Depends(get_extension_user)
):
    """全てのクライアントの採用要件一覧を取得（クライアント情報含む）"""
    try:
        supabase = get_supabase_client()
        
        # job_requirementsテーブルとclientsテーブルをJOIN
        # client_idを明示的に含める（statusカラムを除外）
        query = supabase.table('job_requirements').select('id, title, description, client_id, is_active, created_at, structured_data, client:clients(*)')
        
        if active_only:
            query = query.eq('is_active', True)
        
        # ユーザーのロールに基づいてフィルタリング
        if current_user["role"] != "admin":
            # 管理者以外は自分が担当するクライアントの要件のみ
            # TODO: ユーザーとクライアントの関連付けが必要
            pass
        
        result = query.order('created_at', desc=True).execute()
        
        # レスポンスを整形（クライアント名を含める）
        requirements = []
        for req in result.data:
            requirement = req.copy()
            
            # client_idが確実に含まれるようにする
            if 'client_id' not in requirement:
                if 'client' in requirement and requirement['client'] and 'id' in requirement['client']:
                    requirement['client_id'] = requirement['client']['id']
                else:
                    continue  # client_idがない要件はスキップ
            
            if 'client' in requirement and requirement['client']:
                requirement['client_name'] = requirement['client']['name']
            
            # statusフィールドがない場合は、is_activeから推測
            if 'status' not in requirement:
                requirement['status'] = 'active' if requirement.get('is_active', True) else 'inactive'
            
            requirements.append(requirement)
        
        return requirements
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"採用要件の取得に失敗しました: {str(e)}"
        )

@router.get("/requirements/{requirement_id}", response_model=RequirementResponse)
async def get_requirement(
    requirement_id: str,
    current_user: dict = Depends(get_extension_user)
):
    """特定の採用要件を取得"""
    try:
        supabase = get_supabase_client()
        
        result = supabase.table('job_requirements').select('*').eq('id', requirement_id).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=404,
                detail="採用要件が見つかりません"
            )
        
        return result.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="採用要件の取得に失敗しました"
        )

class StartScrapingRequest(BaseModel):
    client_id: str
    requirement_id: str

@router.post("/scraping/start")
async def start_scraping_session(
    request: StartScrapingRequest,
    current_user: dict = Depends(get_extension_user)
):
    """スクレイピングセッションを開始"""
    try:
        # client_idとrequirement_idの検証
        if not request.client_id or request.client_id == "undefined":
            raise HTTPException(
                status_code=400,
                detail="クライアントIDが無効です"
            )
        
        if not request.requirement_id or request.requirement_id == "undefined":
            raise HTTPException(
                status_code=400,
                detail="採用要件IDが無効です"
            )
        
        supabase = get_supabase_client()
        
        # セッションを作成
        session_data = {
            "user_id": current_user["id"],
            "client_id": request.client_id,
            "requirement_id": request.requirement_id,
            "status": "active",
            "started_at": datetime.utcnow().isoformat(),
            "source": "chrome_extension"
        }
        
        result = supabase.table('scraping_sessions').insert(session_data).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=500,
                detail="セッションの作成に失敗しました"
            )
        
        return {
            "session_id": result.data[0]["id"],
            "status": "active"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"セッションの開始に失敗しました: {str(e)}"
        )

@router.post("/candidates/batch")
async def save_candidates_batch(
    request: BatchCandidateRequest,
    current_user: dict = Depends(get_extension_user)
):
    """候補者データをバッチで保存（新しいテーブル構造）"""
    try:
        supabase = get_supabase_client()
        
        # 候補者データを整形
        candidates_data = []
        
        for candidate in request.candidates:
            # 新しいテーブル構造に合わせたデータ準備
            candidate_data = {
                # 必須フィールド
                'candidate_id': candidate.candidate_id,
                'candidate_link': candidate.candidate_link,
                'candidate_company': candidate.candidate_company,
                'candidate_resume': candidate.candidate_resume,
                'platform': candidate.platform,
                
                # リレーション
                'client_id': candidate.client_id,
                'requirement_id': candidate.requirement_id,
                'scraping_session_id': candidate.scraping_session_id or request.session_id,
                
                # メタデータ
                'scraped_at': datetime.utcnow().isoformat(),
                'scraped_by': current_user["id"],  # ユーザーID (UUID)
                
            }
            
            
            
            candidates_data.append(candidate_data)
        
        # candidatesテーブルにバッチ挿入
        if candidates_data:
            insert_result = supabase.table('candidates').insert(candidates_data).execute()
            
            if not insert_result.data:
                raise HTTPException(
                    status_code=500,
                    detail="候補者データの保存に失敗しました"
                )
        
        # セッションの統計を更新
        session_update = {
            "last_activity": datetime.utcnow().isoformat(),
            "candidates_count": len(candidates_data)
        }
        
        supabase.table('scraping_sessions').update(session_update).eq('id', request.session_id).execute()
        
        return {
            "success": True,
            "processed": len(candidates_data),
            "session_id": request.session_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        # エラーメッセージを詳細にする
        error_message = f"候補者データの保存に失敗しました: {str(e)}"
        
        raise HTTPException(
            status_code=500,
            detail=error_message
        )

@router.post("/scraping/end")
async def end_scraping_session(
    session_id: str,
    current_user: dict = Depends(get_extension_user)
):
    """スクレイピングセッションを終了"""
    try:
        supabase = get_supabase_client()
        
        # セッションを更新
        session_update = {
            "status": "completed",
            "ended_at": datetime.utcnow().isoformat()
        }
        
        result = supabase.table('scraping_sessions').update(session_update).eq('id', session_id).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=404,
                detail="セッションが見つかりません"
            )
        
        return {
            "success": True,
            "session_id": session_id,
            "status": "completed"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="セッションの終了に失敗しました"
        )