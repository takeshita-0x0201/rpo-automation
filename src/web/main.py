"""
RPO Automation WebApp Main Application
FastAPI-based web application entry point
"""

from fastapi import FastAPI, Request, HTTPException, Depends, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
import uvicorn
import os
import json
from datetime import datetime
from typing import Optional

# ルーターのインポート
from src.web.routers import requirements, jobs, results, auth, clients, users, admin_requirements, auth_extension, extension_api, manager, manager_clients, manager_requirements, candidates, job_postings

# FastAPIアプリケーションの初期化
app = FastAPI(
    title="RPO Automation System",
    description="AI・RPAツールを活用したRPO業務自動化システム",
    version="1.0.0"
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "chrome-extension://*",  # Chrome拡張機能からのアクセスを許可
        "https://*.bizreach.jp"  # Bizreachドメインからのアクセスを許可
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静的ファイルとテンプレートの設定
import pathlib
base_dir = pathlib.Path(__file__).parent
app.mount("/static", StaticFiles(directory=str(base_dir / "static")), name="static")
templates = Jinja2Templates(directory=str(base_dir / "templates"))

# ルーターの登録
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(auth_extension.router, tags=["extension-auth"])  # 拡張機能用認証
app.include_router(extension_api.router, tags=["extension-api"])  # 拡張機能用API
app.include_router(requirements.router, prefix="/api/requirements", tags=["requirements"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(results.router, prefix="/api/results", tags=["results"])
app.include_router(clients.router, prefix="/admin/clients", tags=["clients"])
app.include_router(users.router, prefix="/admin/users", tags=["users"])
# 管理者用採用要件ルーター（HTMLページ用）
app.include_router(admin_requirements.router, tags=["admin_requirements"])
# マネージャー用ルーター
app.include_router(manager.router, tags=["manager"])
app.include_router(manager_clients.router, prefix="/manager/clients", tags=["manager_clients"])
app.include_router(manager_requirements.router, tags=["manager_requirements"])
# 候補者管理ルーター
app.include_router(candidates.router, prefix="/candidates", tags=["candidates"])
# 求人票管理ルーター
app.include_router(job_postings.router, tags=["job_postings"])

from src.web.routers.auth import get_current_user_from_cookie

# ルートエンドポイント
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """メインページ（ログインページへリダイレクト）"""
    return RedirectResponse(url="/login", status_code=303)

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, user: Optional[dict] = Depends(get_current_user_from_cookie)):
    """ログインページ"""
    error = request.query_params.get("error")
    return templates.TemplateResponse("common/login.html", {"request": request, "error": error, "current_user": user})

@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request, user: Optional[dict] = Depends(get_current_user_from_cookie)):
    """管理者ダッシュボード"""
    if not user or user.get("role") != "admin":
        return RedirectResponse(url="/login?error=Unauthorized", status_code=303)
    return templates.TemplateResponse("admin/admin_dashboard.html", {"request": request, "current_user": user})

@app.get("/manager", response_class=HTMLResponse)
async def manager_dashboard(request: Request, user: Optional[dict] = Depends(get_current_user_from_cookie)):
    """マネージャーダッシュボード"""
    if not user or user.get("role") != "manager":
        return RedirectResponse(url="/login?error=Unauthorized", status_code=303)
    return templates.TemplateResponse("admin/admin_dashboard.html", {"request": request, "current_user": user})

@app.get("/user", response_class=HTMLResponse)
async def user_dashboard(request: Request, user: Optional[dict] = Depends(get_current_user_from_cookie)):
    """ユーザーダッシュボード"""
    if not user:
        return RedirectResponse(url="/login?error=Unauthorized", status_code=303)
    return templates.TemplateResponse("user/user_dashboard.html", {"request": request, "current_user": user})

@app.get("/logout")
async def logout(request: Request):
    """ログアウト"""
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("access_token")
    return response

# 管理者向けページ

@app.get("/admin/jobs", response_class=HTMLResponse)
async def admin_jobs(request: Request, user: Optional[dict] = Depends(get_current_user_from_cookie)):
    """管理者 - ジョブ管理"""
    if not user or user.get("role") != "admin":
        return RedirectResponse(url="/login?error=Unauthorized", status_code=303)
    
    try:
        from src.utils.supabase_client import get_supabase_client
        from src.services.candidate_counter import CandidateCounter
        
        supabase = get_supabase_client()
        candidate_counter = CandidateCounter()
        
        # ジョブ一覧を取得（クライアント情報と一緒に）
        jobs_response = supabase.table('jobs').select('*, client:clients(name)').order('created_at', desc=True).execute()
        jobs = jobs_response.data if jobs_response.data else []
        
        # クライアント名を展開と対象候補者数を追加
        for job in jobs:
            if 'client' in job and job['client']:
                job['client_name'] = job['client']['name']
            else:
                job['client_name'] = 'N/A'
            
            # 対象候補者数を取得
            if job.get('status') == 'completed':
                # 完了したジョブは実際の処理数を表示
                job['candidate_count'] = job.get('candidate_count', 0)
            elif job.get('status') in ['pending', 'ready', 'running']:
                # 未実行・実行中のジョブは推定値を取得
                job_params = job.get('parameters', {})
                client_id = job.get('client_id')
                requirement_id = job.get('requirement_id')
                
                # Supabaseから実際の候補者数を取得
                actual_count = candidate_counter.count_candidates(job_params, client_id, requirement_id)
                if actual_count is not None:
                    job['candidate_count'] = actual_count
                else:
                    # Supabase接続エラー時はエラーメッセージを表示
                    job['candidate_count'] = candidate_counter.get_error_message()
            else:
                job['candidate_count'] = 0
        
        # ステータス別カウント
        running_count = sum(1 for j in jobs if j.get('status') == 'running')
        completed_count = sum(1 for j in jobs if j.get('status') == 'completed')
        pending_count = sum(1 for j in jobs if j.get('status') in ['pending', 'ready'])
        error_count = sum(1 for j in jobs if j.get('status') == 'failed')
        
    except Exception as e:
        print(f"Error fetching jobs: {e}")
        jobs = []
        running_count = completed_count = pending_count = error_count = 0
    
    return templates.TemplateResponse("admin/jobs.html", {
        "request": request, 
        "current_user": user, 
        "jobs": jobs,
        "running_count": running_count,
        "completed_count": completed_count,
        "pending_count": pending_count,
        "error_count": error_count
    })

@app.get("/admin/jobs/new", response_class=HTMLResponse)
async def admin_jobs_new(request: Request, user: Optional[dict] = Depends(get_current_user_from_cookie)):
    """管理者 - 新規ジョブ作成"""
    if not user or user.get("role") != "admin":
        return RedirectResponse(url="/login?error=Unauthorized", status_code=303)
    
    try:
        from src.utils.supabase_client import get_supabase_client
        supabase = get_supabase_client()
        
        # クライアント一覧を取得
        clients_response = supabase.table('clients').select('id, name').eq('is_active', True).order('name').execute()
        clients = clients_response.data if clients_response.data else []
        
    except Exception as e:
        print(f"Error fetching clients: {e}")
        clients = []
    
    return templates.TemplateResponse("admin/job_new.html", {
        "request": request, 
        "current_user": user, 
        "clients": clients
    })

@app.post("/admin/jobs/create", response_class=HTMLResponse)
async def admin_jobs_create(
    request: Request,
    job_name: str = Form(...),
    client_id: str = Form(...),
    requirement_id: str = Form(...),
    data_source: str = Form("latest"),
    start_date: Optional[str] = Form(None),
    end_date: Optional[str] = Form(None),
    matching_threshold: str = Form("high"),
    output_sheets: bool = Form(False),
    output_bigquery: bool = Form(False),
    priority: str = Form("normal"),
    notify_completion: bool = Form(False),
    user: Optional[dict] = Depends(get_current_user_from_cookie)
):
    """管理者 - AIマッチングジョブ作成処理"""
    if not user or user.get("role") != "admin":
        return RedirectResponse(url="/login?error=Unauthorized", status_code=303)
    
    try:
        from src.utils.supabase_client import get_supabase_client
        from datetime import datetime
        import uuid
        
        supabase = get_supabase_client()
        
        # ジョブデータを構築
        job_data = {
            "id": str(uuid.uuid4()),
            "job_type": "ai_matching",  # AIマッチング固定
            "client_id": client_id,
            "requirement_id": requirement_id,
            "name": job_name,
            "status": "pending",  # 常にpendingで作成
            "priority": priority,
            "created_by": user['id'],
            "created_at": datetime.utcnow().isoformat(),
            "parameters": {
                "data_source": data_source,
                "matching_threshold": matching_threshold,
                "output_sheets": output_sheets,
                "output_bigquery": output_bigquery,
                "notify_completion": notify_completion
            }
        }
        
        # 期間指定の場合は日付を追加
        if data_source == "date_range" and start_date and end_date:
            job_data["parameters"]["start_date"] = start_date
            job_data["parameters"]["end_date"] = end_date
        
        # ジョブを保存
        print(f"Saving job to Supabase: {job_data}")
        result = supabase.table('jobs').insert(job_data).execute()
        
        if result.data:
            print(f"Job created successfully: {result.data[0]['id']}")
            return RedirectResponse(url="/admin/jobs?success=created", status_code=303)
        else:
            print(f"Failed to create job: No data returned")
            return RedirectResponse(url="/admin/jobs/new?error=create_failed", status_code=303)
            
    except Exception as e:
        print(f"Error creating job: {e}")
        return RedirectResponse(url="/admin/jobs/new?error=create_failed", status_code=303)

@app.post("/admin/jobs/{job_id}/execute")
async def admin_job_execute(job_id: str, user: Optional[dict] = Depends(get_current_user_from_cookie)):
    """管理者 - ジョブ実行"""
    if not user or user.get("role") != "admin":
        return JSONResponse(status_code=403, content={"error": "Unauthorized"})
    
    try:
        from src.utils.supabase_client import get_supabase_client
        from datetime import datetime
        
        supabase = get_supabase_client()
        
        # ジョブのステータスを更新
        result = supabase.table('jobs').update({
            "status": "running",
            "started_at": datetime.utcnow().isoformat()
        }).eq('id', job_id).eq('status', 'pending').execute()
        
        if result.data:
            # TODO: 実際のジョブ実行処理をキューに追加
            # ここでは仮実装としてステータス更新のみ
            return JSONResponse(status_code=200, content={"success": True})
        else:
            return JSONResponse(status_code=404, content={"error": "Job not found or already running"})
            
    except Exception as e:
        print(f"Error executing job: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/admin/jobs/{job_id}/cancel")
async def admin_job_cancel(job_id: str, user: Optional[dict] = Depends(get_current_user_from_cookie)):
    """管理者 - ジョブ停止"""
    if not user or user.get("role") != "admin":
        return JSONResponse(status_code=403, content={"error": "Unauthorized"})
    
    try:
        from src.utils.supabase_client import get_supabase_client
        from datetime import datetime
        
        supabase = get_supabase_client()
        
        # ジョブのステータスを更新
        result = supabase.table('jobs').update({
            "status": "failed",
            "completed_at": datetime.utcnow().isoformat(),
            "error_message": "ユーザーによって停止されました"
        }).eq('id', job_id).eq('status', 'running').execute()
        
        if result.data:
            print(f"Job cancelled successfully: {job_id}")
            return JSONResponse(status_code=200, content={"success": True})
        else:
            return JSONResponse(status_code=404, content={"error": "Job not found or not running"})
            
    except Exception as e:
        print(f"Error cancelling job: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.delete("/admin/jobs/{job_id}/delete")
async def admin_job_delete(job_id: str, user: Optional[dict] = Depends(get_current_user_from_cookie)):
    """管理者 - ジョブ削除"""
    if not user or user.get("role") != "admin":
        return JSONResponse(status_code=403, content={"error": "Unauthorized"})
    
    try:
        from src.utils.supabase_client import get_supabase_client
        
        supabase = get_supabase_client()
        
        # 実行中のジョブは削除不可
        job_check = supabase.table('jobs').select('status').eq('id', job_id).execute()
        if job_check.data and job_check.data[0]['status'] == 'running':
            return JSONResponse(status_code=400, content={"error": "実行中のジョブは削除できません"})
        
        # ジョブを削除
        result = supabase.table('jobs').delete().eq('id', job_id).execute()
        
        if result.data:
            print(f"Job deleted successfully: {job_id}")
            return JSONResponse(status_code=200, content={"success": True})
        else:
            return JSONResponse(status_code=404, content={"error": "Job not found"})
            
    except Exception as e:
        print(f"Error deleting job: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/manager/jobs", response_class=HTMLResponse)
async def manager_jobs(request: Request, user: Optional[dict] = Depends(get_current_user_from_cookie)):
    """マネージャー - ジョブ管理"""
    if not user or user.get("role") != "manager":
        return RedirectResponse(url="/login?error=Unauthorized", status_code=303)
    
    try:
        from src.utils.supabase_client import get_supabase_client
        from src.services.candidate_counter import CandidateCounter
        
        supabase = get_supabase_client()
        candidate_counter = CandidateCounter()
        
        # ジョブ一覧を取得（クライアント情報と一緒に）
        jobs_response = supabase.table('jobs').select('*, client:clients(name)').order('created_at', desc=True).execute()
        jobs = jobs_response.data if jobs_response.data else []
        
        # クライアント名を展開と対象候補者数を追加
        for job in jobs:
            if 'client' in job and job['client']:
                job['client_name'] = job['client']['name']
            else:
                job['client_name'] = 'N/A'
            
            # 対象候補者数を取得
            if job.get('status') == 'completed':
                # 完了したジョブは実際の処理数を表示
                job['candidate_count'] = job.get('candidate_count', 0)
            elif job.get('status') in ['pending', 'ready', 'running']:
                # 未実行・実行中のジョブは推定値を取得
                job_params = job.get('parameters', {})
                client_id = job.get('client_id')
                requirement_id = job.get('requirement_id')
                
                # Supabaseから実際の候補者数を取得
                actual_count = candidate_counter.count_candidates(job_params, client_id, requirement_id)
                if actual_count is not None:
                    job['candidate_count'] = actual_count
                else:
                    # Supabase接続エラー時はエラーメッセージを表示
                    job['candidate_count'] = candidate_counter.get_error_message()
            else:
                job['candidate_count'] = 0
        
        # ステータス別カウント
        running_count = sum(1 for j in jobs if j.get('status') == 'running')
        completed_count = sum(1 for j in jobs if j.get('status') == 'completed')
        pending_count = sum(1 for j in jobs if j.get('status') in ['pending', 'ready'])
        error_count = sum(1 for j in jobs if j.get('status') == 'failed')
        
    except Exception as e:
        print(f"Error fetching jobs: {e}")
        jobs = []
        running_count = completed_count = pending_count = error_count = 0
    
    return templates.TemplateResponse("admin/jobs.html", {
        "request": request, 
        "current_user": user, 
        "jobs": jobs,
        "running_count": running_count,
        "completed_count": completed_count,
        "pending_count": pending_count,
        "error_count": error_count
    })

@app.get("/manager/jobs/new", response_class=HTMLResponse)
async def manager_jobs_new(request: Request, user: Optional[dict] = Depends(get_current_user_from_cookie)):
    """マネージャー - 新規ジョブ作成"""
    if not user or user.get("role") != "manager":
        return RedirectResponse(url="/login?error=Unauthorized", status_code=303)
    
    try:
        from src.utils.supabase_client import get_supabase_client
        supabase = get_supabase_client()
        
        # クライアント一覧を取得
        clients_response = supabase.table('clients').select('id, name').eq('is_active', True).order('name').execute()
        clients = clients_response.data if clients_response.data else []
        
    except Exception as e:
        print(f"Error fetching clients: {e}")
        clients = []
    
    return templates.TemplateResponse("admin/job_new.html", {
        "request": request, 
        "current_user": user, 
        "clients": clients
    })

@app.post("/manager/jobs/create", response_class=HTMLResponse)
async def manager_jobs_create(
    request: Request,
    job_name: str = Form(...),
    client_id: str = Form(...),
    requirement_id: str = Form(...),
    data_source: str = Form("latest"),
    start_date: Optional[str] = Form(None),
    end_date: Optional[str] = Form(None),
    matching_threshold: str = Form("high"),
    output_sheets: bool = Form(False),
    output_bigquery: bool = Form(False),
    priority: str = Form("normal"),
    notify_completion: bool = Form(False),
    user: Optional[dict] = Depends(get_current_user_from_cookie)
):
    """マネージャー - AIマッチングジョブ作成処理"""
    if not user or user.get("role") != "manager":
        return RedirectResponse(url="/login?error=Unauthorized", status_code=303)
    
    try:
        from src.utils.supabase_client import get_supabase_client
        from datetime import datetime
        import uuid
        
        supabase = get_supabase_client()
        
        # ジョブデータを構築
        job_data = {
            "id": str(uuid.uuid4()),
            "job_type": "ai_matching",  # AIマッチング固定
            "client_id": client_id,
            "requirement_id": requirement_id,
            "name": job_name,
            "status": "pending",  # 常にpendingで作成
            "priority": priority,
            "created_by": user['id'],
            "created_at": datetime.utcnow().isoformat(),
            "parameters": {
                "data_source": data_source,
                "matching_threshold": matching_threshold,
                "output_sheets": output_sheets,
                "output_bigquery": output_bigquery,
                "notify_completion": notify_completion
            }
        }
        
        # 期間指定の場合は日付を追加
        if data_source == "date_range" and start_date and end_date:
            job_data["parameters"]["start_date"] = start_date
            job_data["parameters"]["end_date"] = end_date
        
        # ジョブを保存
        print(f"Saving job to Supabase: {job_data}")
        result = supabase.table('jobs').insert(job_data).execute()
        
        if result.data:
            print(f"Job created successfully: {result.data[0]['id']}")
            return RedirectResponse(url="/manager/jobs?success=created", status_code=303)
        else:
            print(f"Failed to create job: No data returned")
            return RedirectResponse(url="/manager/jobs/new?error=create_failed", status_code=303)
            
    except Exception as e:
        print(f"Error creating job: {e}")
        return RedirectResponse(url="/manager/jobs/new?error=create_failed", status_code=303)

@app.post("/manager/jobs/{job_id}/execute")
async def manager_job_execute(job_id: str, user: Optional[dict] = Depends(get_current_user_from_cookie)):
    """マネージャー - ジョブ実行"""
    if not user or user.get("role") != "manager":
        return JSONResponse(status_code=403, content={"error": "Unauthorized"})
    
    try:
        from src.utils.supabase_client import get_supabase_client
        from datetime import datetime
        
        supabase = get_supabase_client()
        
        # ジョブのステータスを更新
        result = supabase.table('jobs').update({
            "status": "running",
            "started_at": datetime.utcnow().isoformat()
        }).eq('id', job_id).eq('status', 'pending').execute()
        
        if result.data:
            # TODO: 実際のジョブ実行処理をキューに追加
            # ここでは仮実装としてステータス更新のみ
            return JSONResponse(status_code=200, content={"success": True})
        else:
            return JSONResponse(status_code=404, content={"error": "Job not found or already running"})
            
    except Exception as e:
        print(f"Error executing job: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/manager/jobs/{job_id}/cancel")
async def manager_job_cancel(job_id: str, user: Optional[dict] = Depends(get_current_user_from_cookie)):
    """マネージャー - ジョブ停止"""
    if not user or user.get("role") != "manager":
        return JSONResponse(status_code=403, content={"error": "Unauthorized"})
    
    try:
        from src.utils.supabase_client import get_supabase_client
        from datetime import datetime
        
        supabase = get_supabase_client()
        
        # ジョブのステータスを更新
        result = supabase.table('jobs').update({
            "status": "failed",
            "completed_at": datetime.utcnow().isoformat(),
            "error_message": "ユーザーによって停止されました"
        }).eq('id', job_id).eq('status', 'running').execute()
        
        if result.data:
            print(f"Job cancelled successfully: {job_id}")
            return JSONResponse(status_code=200, content={"success": True})
        else:
            return JSONResponse(status_code=404, content={"error": "Job not found or not running"})
            
    except Exception as e:
        print(f"Error cancelling job: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.delete("/manager/jobs/{job_id}/delete")
async def manager_job_delete(job_id: str, user: Optional[dict] = Depends(get_current_user_from_cookie)):
    """マネージャー - ジョブ削除"""
    if not user or user.get("role") != "manager":
        return JSONResponse(status_code=403, content={"error": "Unauthorized"})
    
    try:
        from src.utils.supabase_client import get_supabase_client
        
        supabase = get_supabase_client()
        
        # 実行中のジョブは削除不可
        job_check = supabase.table('jobs').select('status').eq('id', job_id).execute()
        if job_check.data and job_check.data[0]['status'] == 'running':
            return JSONResponse(status_code=400, content={"error": "実行中のジョブは削除できません"})
        
        # ジョブを削除
        result = supabase.table('jobs').delete().eq('id', job_id).execute()
        
        if result.data:
            print(f"Job deleted successfully: {job_id}")
            return JSONResponse(status_code=200, content={"success": True})
        else:
            return JSONResponse(status_code=404, content={"error": "Job not found"})
            
    except Exception as e:
        print(f"Error deleting job: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/admin/analytics", response_class=HTMLResponse)
async def admin_analytics(request: Request, user: Optional[dict] = Depends(get_current_user_from_cookie)):
    """管理者 - 分析レポート"""
    if not user or user.get("role") != "admin":
        return RedirectResponse(url="/login?error=Unauthorized", status_code=303)
    # TODO: 分析データを取得
    client_stats = []
    return templates.TemplateResponse("admin/analytics.html", {"request": request, "current_user": user, "client_stats": client_stats})

@app.get("/manager/analytics", response_class=HTMLResponse)
async def manager_analytics(request: Request, user: Optional[dict] = Depends(get_current_user_from_cookie)):
    """マネージャー - 分析レポート"""
    if not user or user.get("role") != "manager":
        return RedirectResponse(url="/login?error=Unauthorized", status_code=303)
    # TODO: 分析データを取得
    client_stats = []
    return templates.TemplateResponse("admin/analytics.html", {"request": request, "current_user": user, "client_stats": client_stats})

@app.get("/admin/settings", response_class=HTMLResponse)
async def admin_settings(request: Request, user: Optional[dict] = Depends(get_current_user_from_cookie)):
    """管理者 - システム設定"""
    if not user or user.get("role") != "admin":
        return RedirectResponse(url="/login?error=Unauthorized", status_code=303)
    # TODO: 設定データを取得
    settings = {}
    return templates.TemplateResponse("admin/settings.html", {"request": request, "current_user": user, "settings": settings})


# ユーザー向けページ
@app.get("/user/requirements", response_class=HTMLResponse)
async def user_requirements(request: Request, user: Optional[dict] = Depends(get_current_user_from_cookie)):
    """ユーザー - 採用要件"""
    if not user:
        return RedirectResponse(url="/login?error=Unauthorized", status_code=303)
    
    try:
        from src.utils.supabase_client import get_supabase_client
        supabase = get_supabase_client()
        
        # クライアント一覧を取得
        clients_response = supabase.table('clients').select('id, name').eq('is_active', True).execute()
        clients = clients_response.data if clients_response.data else []
        
        # 採用要件を取得（クライアント情報を含む）
        req_response = supabase.table('job_requirements').select('*, client:clients(name)').eq('is_active', True).order('created_at', desc=True).execute()
        requirements = req_response.data if req_response.data else []
        
        # クライアント名を展開
        for req in requirements:
            if 'client' in req and req['client']:
                req['client_name'] = req['client']['name']
            else:
                req['client_name'] = 'N/A'
                
    except Exception as e:
        print(f"Error fetching requirements: {e}")
        requirements = []
        clients = []
    
    return templates.TemplateResponse("user/requirements.html", {
        "request": request, 
        "current_user": user, 
        "requirements": requirements,
        "clients": clients
    })

@app.get("/user/requirements/new", response_class=HTMLResponse)
async def user_requirement_new_form(request: Request, user: Optional[dict] = Depends(get_current_user_from_cookie)):
    """ユーザー - 新規採用要件作成フォーム"""
    if not user:
        return RedirectResponse(url="/login?error=Unauthorized", status_code=303)
    
    # manager/adminのみアクセス可能
    if user.get('role') not in ['manager', 'admin']:
        return RedirectResponse(url="/user/requirements?error=permission_denied", status_code=303)
    
    try:
        from src.utils.supabase_client import get_supabase_client
        supabase = get_supabase_client()
        
        # クライアント一覧を取得
        clients_response = supabase.table('clients').select('id, name').eq('is_active', True).execute()
        clients = clients_response.data if clients_response.data else []
            
    except Exception as e:
        print(f"Error fetching clients: {e}")
        clients = []
    
    return templates.TemplateResponse("user/requirement_new.html", {
        "request": request,
        "current_user": user,
        "clients": clients
    })

@app.post("/user/requirements/new", response_class=HTMLResponse)
async def user_requirement_create(
    request: Request,
    title: str = Form(...),
    client_id: str = Form(...),
    description: str = Form(...),
    structured_data: str = Form(...),
    is_active: bool = Form(False),
    user: Optional[dict] = Depends(get_current_user_from_cookie)
):
    """ユーザー - 採用要件作成"""
    if not user:
        return RedirectResponse(url="/login?error=Unauthorized", status_code=303)
    
    # manager/adminのみアクセス可能
    if user.get('role') not in ['manager', 'admin']:
        return RedirectResponse(url="/user/requirements?error=permission_denied", status_code=303)
    
    try:
        from src.utils.supabase_client import get_supabase_client
        supabase = get_supabase_client()
        
        # 構造化データをパース
        try:
            structured_data_json = json.loads(structured_data)
        except:
            structured_data_json = {}
        
        # 採用要件を作成
        insert_data = {
            "title": title,
            "client_id": client_id,
            "description": description,
            "structured_data": structured_data_json,
            "is_active": is_active,
            "created_by": user['id'],
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        result = supabase.table('job_requirements').insert(insert_data).execute()
        
        if result.data and len(result.data) > 0:
            new_id = result.data[0]['id']
            return RedirectResponse(url=f"/user/requirements/{new_id}?success=created", status_code=303)
        else:
            return RedirectResponse(url="/user/requirements/new?error=create_failed", status_code=303)
        
    except Exception as e:
        print(f"Error creating requirement: {e}")
        return RedirectResponse(url="/user/requirements/new?error=create_failed", status_code=303)

@app.get("/user/requirements/{requirement_id}", response_class=HTMLResponse)
async def user_requirement_detail(request: Request, requirement_id: str, user: Optional[dict] = Depends(get_current_user_from_cookie)):
    """ユーザー - 採用要件詳細"""
    if not user:
        return RedirectResponse(url="/login?error=Unauthorized", status_code=303)
    
    try:
        from src.utils.supabase_client import get_supabase_client
        supabase = get_supabase_client()
        
        # 採用要件を取得
        req_response = supabase.table('job_requirements').select('*, client:clients(name)').eq('id', requirement_id).single().execute()
        requirement = req_response.data
        
        if requirement and 'client' in requirement and requirement['client']:
            requirement['client_name'] = requirement['client']['name']
        else:
            requirement['client_name'] = 'N/A' if requirement else None
            
        if not requirement:
            return RedirectResponse(url="/user/requirements", status_code=303)
            
        # この要件に関連するジョブ履歴を取得
        jobs_response = supabase.table('jobs').select('*').eq('requirement_id', requirement_id).eq('created_by', user['id']).order('started_at', desc=True).limit(10).execute()
        jobs = jobs_response.data if jobs_response.data else []
        
        # ジョブデータを整形
        for job in jobs:
            status_map = {
                'running': ('実行中', 'primary'),
                'paused': ('一時停止', 'warning'),
                'completed': ('完了', 'success'),
                'failed': ('失敗', 'danger'),
                'stopped': ('停止', 'secondary')
            }
            job['status_display'], job['status_color'] = status_map.get(job['status'], ('不明', 'info'))
            
        success = request.query_params.get("success")
            
    except Exception as e:
        print(f"Error fetching requirement: {e}")
        return RedirectResponse(url="/user/requirements", status_code=303)
    
    return templates.TemplateResponse("user/requirement_detail.html", {
        "request": request,
        "current_user": user,
        "requirement": requirement,
        "jobs": jobs,
        "success": success
    })

@app.get("/user/requirements/{requirement_id}/edit", response_class=HTMLResponse)
async def user_requirement_edit_form(request: Request, requirement_id: str, user: Optional[dict] = Depends(get_current_user_from_cookie)):
    """ユーザー - 採用要件編集フォーム"""
    if not user:
        return RedirectResponse(url="/login?error=Unauthorized", status_code=303)
    
    # manager/adminのみアクセス可能
    if user.get('role') not in ['manager', 'admin']:
        return RedirectResponse(url="/user/requirements?error=permission_denied", status_code=303)
    
    try:
        from src.utils.supabase_client import get_supabase_client
        supabase = get_supabase_client()
        
        # 採用要件を取得
        req_response = supabase.table('job_requirements').select('*').eq('id', requirement_id).single().execute()
        requirement = req_response.data
        
        if not requirement:
            return RedirectResponse(url="/user/requirements", status_code=303)
            
        # クライアント一覧を取得
        clients_response = supabase.table('clients').select('id, name').eq('is_active', True).execute()
        clients = clients_response.data if clients_response.data else []
            
    except Exception as e:
        print(f"Error fetching requirement: {e}")
        return RedirectResponse(url="/user/requirements", status_code=303)
    
    return templates.TemplateResponse("user/requirement_edit.html", {
        "request": request,
        "current_user": user,
        "requirement": requirement,
        "clients": clients
    })

@app.post("/user/requirements/{requirement_id}/edit", response_class=HTMLResponse)
async def user_requirement_edit(
    request: Request, 
    requirement_id: str,
    title: str = Form(...),
    client_id: str = Form(...),
    description: str = Form(...),
    structured_data: str = Form(...),
    is_active: bool = Form(False),
    user: Optional[dict] = Depends(get_current_user_from_cookie)
):
    """ユーザー - 採用要件更新"""
    if not user:
        return RedirectResponse(url="/login?error=Unauthorized", status_code=303)
    
    # manager/adminのみアクセス可能
    if user.get('role') not in ['manager', 'admin']:
        return RedirectResponse(url="/user/requirements?error=permission_denied", status_code=303)
    
    try:
        from src.utils.supabase_client import get_supabase_client
        supabase = get_supabase_client()
        
        # 構造化データをパース
        try:
            structured_data_json = json.loads(structured_data)
        except:
            structured_data_json = {}
        
        # 採用要件を更新
        update_data = {
            "title": title,
            "client_id": client_id,
            "description": description,
            "structured_data": structured_data_json,
            "is_active": is_active,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        supabase.table('job_requirements').update(update_data).eq('id', requirement_id).execute()
        
        return RedirectResponse(url=f"/user/requirements/{requirement_id}?success=updated", status_code=303)
        
    except Exception as e:
        print(f"Error updating requirement: {e}")
        return RedirectResponse(url=f"/user/requirements/{requirement_id}/edit?error=update_failed", status_code=303)

@app.get("/user/jobs", response_class=HTMLResponse)
async def user_jobs(request: Request, user: Optional[dict] = Depends(get_current_user_from_cookie)):
    """ユーザー - ジョブ実行"""
    if not user:
        return RedirectResponse(url="/login?error=Unauthorized", status_code=303)
    
    try:
        from src.utils.supabase_client import get_supabase_client
        supabase = get_supabase_client()
        
        # アクティブな採用要件を取得
        req_response = supabase.table('job_requirements').select('id, title, client:clients(name)').eq('is_active', True).eq('status', 'active').order('created_at', desc=True).execute()
        active_requirements = req_response.data if req_response.data else []
        
        # クライアント名を展開
        for req in active_requirements:
            if 'client' in req and req['client']:
                req['client_name'] = req['client']['name']
            else:
                req['client_name'] = 'N/A'
        
        # 実行中のジョブを取得
        active_jobs_response = supabase.table('jobs').select('*, requirement:job_requirements(title)').in_('status', ['running', 'paused']).eq('created_by', user['id']).order('created_at', desc=True).execute()
        active_jobs = active_jobs_response.data if active_jobs_response.data else []
        
        # ジョブ履歴を取得（ページネーション付き）
        current_page = int(request.query_params.get("page", 1))
        per_page = 10
        offset = (current_page - 1) * per_page
        
        # 完了済みジョブの総数を取得
        count_response = supabase.table('jobs').select('id', count='exact').in_('status', ['completed', 'failed', 'stopped']).eq('created_by', user['id']).execute()
        total_count = count_response.count if hasattr(count_response, 'count') else 0
        total_pages = (total_count + per_page - 1) // per_page
        
        # ジョブ履歴を取得
        history_response = supabase.table('jobs').select('*, requirement:job_requirements(title)').in_('status', ['completed', 'failed', 'stopped']).eq('created_by', user['id']).order('completed_at', desc=True).limit(per_page).offset(offset).execute()
        job_history = history_response.data if history_response.data else []
        
        # ジョブデータを整形
        for job in active_jobs + job_history:
            if 'requirement' in job and job['requirement']:
                job['requirement_title'] = job['requirement']['title']
            else:
                job['requirement_title'] = 'N/A'
                
            # ステータス表示用のデータを追加
            status_map = {
                'running': ('実行中', 'primary'),
                'paused': ('一時停止', 'warning'),
                'completed': ('完了', 'success'),
                'failed': ('失敗', 'danger'),
                'stopped': ('停止', 'secondary')
            }
            job['status_display'], job['status_color'] = status_map.get(job['status'], ('不明', 'info'))
            
            # 進捗率を計算
            job['progress'] = int((job.get('processed_count', 0) / job.get('total_count', 1)) * 100) if job.get('total_count', 0) > 0 else 0
            
            # 実行時間を計算
            if job.get('started_at') and job.get('completed_at'):
                from datetime import datetime
                start = datetime.fromisoformat(job['started_at'].replace('Z', '+00:00'))
                end = datetime.fromisoformat(job['completed_at'].replace('Z', '+00:00'))
                duration = end - start
                hours, remainder = divmod(duration.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                job['duration'] = f"{hours}時間{minutes}分" if hours > 0 else f"{minutes}分{seconds}秒"
            else:
                job['duration'] = '-'
                
            # 日時フォーマット
            for field in ['started_at', 'completed_at']:
                if job.get(field):
                    job[field] = job[field].replace('T', ' ').split('.')[0]
                    
    except Exception as e:
        print(f"Error fetching jobs: {e}")
        active_requirements = []
        active_jobs = []
        job_history = []
        current_page = 1
        total_pages = 1
    
    selected_requirement_id = request.query_params.get("requirement_id")
    
    return templates.TemplateResponse("user/jobs.html", {
        "request": request, 
        "current_user": user,
        "active_requirements": active_requirements,
        "active_jobs": active_jobs,
        "job_history": job_history,
        "current_page": current_page,
        "total_pages": total_pages,
        "selected_requirement_id": selected_requirement_id
    })

@app.get("/user/history", response_class=HTMLResponse)
async def user_history(request: Request, user: Optional[dict] = Depends(get_current_user_from_cookie)):
    """ユーザー - 実行履歴"""
    if not user:
        return RedirectResponse(url="/login?error=Unauthorized", status_code=303)
    # TODO: 履歴データを取得
    history = []
    current_page = int(request.query_params.get("page", 1))
    total_pages = 1
    return templates.TemplateResponse("user/history.html", {
        "request": request, 
        "current_user": user, 
        "history": history,
        "current_page": current_page,
        "total_pages": total_pages
    })

# ヘルスチェックエンドポイント
@app.get("/health")
async def health_check():
    """ヘルスチェック"""
    return {"status": "healthy", "service": "rpo-automation-webapp"}

# エラーハンドラー
@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """404エラーハンドラー"""
    user = None
    try:
        user = await get_current_user_from_cookie(request)
    except:
        pass
    return templates.TemplateResponse("common/404.html", {"request": request, "current_user": user}, status_code=404)

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: HTTPException):
    """500エラーハンドラー"""
    user = None
    try:
        user = await get_current_user_from_cookie(request)
    except:
        pass
    return templates.TemplateResponse("common/500.html", {"request": request, "current_user": user}, status_code=500)

# API情報エンドポイント
@app.get("/api/info")
async def api_info():
    """API情報を返す"""
    return {
        "title": app.title,
        "description": app.description,
        "version": app.version,
        "docs_url": "/docs",
        "redoc_url": "/redoc"
    }

if __name__ == "__main__":
    # 開発環境での起動
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True
    )