"""
RPO Automation WebApp Main Application
FastAPI-based web application entry point
"""

# 環境変数を最初に読み込む
from dotenv import load_dotenv
load_dotenv()

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
from routers import requirements, jobs, results, auth, clients, users, admin_requirements, auth_extension, extension_api, manager, manager_clients, manager_requirements, candidates, job_postings, csv_upload, media_platforms, admin_media_platforms
from routers import job_execution, csv_api, sync_api, sync_monitor, client_evaluations, feedback_api  # , matching_api

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
app.include_router(job_execution.router, tags=["job-execution"])  # ジョブ実行管理
# app.include_router(matching_api.router, tags=["matching"])  # AIマッチング
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
# 管理者用候補者ルーター（/admin/candidatesのパスで使用）
app.include_router(candidates.router, prefix="/admin/candidates", tags=["admin_candidates"])
# 求人票管理ルーター
app.include_router(job_postings.router, tags=["job_postings"])
# CSVアップロードルーター
app.include_router(csv_upload.router, tags=["csv_upload"])
# 媒体プラットフォームルーター
app.include_router(media_platforms.router, prefix="/api", tags=["media_platforms"])
# 管理者用媒体プラットフォームルーター
app.include_router(admin_media_platforms.router, tags=["admin_media_platforms"])
# 評価API (削除済み - client_evaluationsに統合)
# CSV API
app.include_router(csv_api.router, tags=["csv"])
# Sync API
app.include_router(sync_api.router, tags=["sync"])
# Sync Monitor
app.include_router(sync_monitor.router, tags=["sync_monitor"])
# クライアント評価API
app.include_router(client_evaluations.router, prefix="/api/client-evaluations", tags=["client_evaluations"])
# フィードバックAPI
app.include_router(feedback_api.router, prefix="/api/feedback", tags=["feedback"])

# ベクトルDB管理（インポートを追加）
# Vector admin removed - functionality moved to Edge Functions

from routers.auth import get_current_user_from_cookie
from core.utils.supabase_client import get_supabase_client

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
        from core.utils.supabase_client import get_supabase_client
        from core.services.candidate_counter import CandidateCounter
        
        supabase = get_supabase_client()
        candidate_counter = CandidateCounter()
        
        # ジョブ一覧を取得（job_idで昇順）
        jobs_response = supabase.table('jobs').select('*').order('job_id', desc=False).execute()
        jobs = jobs_response.data if jobs_response.data else []
        
        # 対象候補者数を追加（改善版）
        for job in jobs:
            try:
                job_id = job.get('id')
                requirement_id = job.get('requirement_id')
                
                if requirement_id:
                    # 全候補者数を取得
                    all_candidates_response = supabase.table('candidates').select(
                        'id', count='exact'
                    ).eq('requirement_id', requirement_id).execute()
                    total_candidates = all_candidates_response.count or 0
                    
                    # 評価済み候補者数を取得
                    evaluated_response = supabase.table('ai_evaluations').select(
                        'id', count='exact'
                    ).eq('job_id', job_id).execute()
                    evaluated_count = evaluated_response.count or 0
                    
                    # 未評価候補者数を計算
                    unevaluated_count = total_candidates - evaluated_count
                    
                    # ジョブのステータスに応じて表示を調整
                    if job.get('status') == 'completed':
                        # 完了したジョブは評価済み数を表示
                        job['candidate_count'] = evaluated_count
                        job['progress_fraction'] = f"{evaluated_count}/{evaluated_count}"
                    else:
                        # 未完了のジョブは未評価数を対象として表示
                        job['candidate_count'] = unevaluated_count
                        job['progress_fraction'] = f"{evaluated_count}/{total_candidates}"
                    
                    job['evaluated_count'] = evaluated_count
                    job['total_candidates'] = total_candidates
                    job['unevaluated_count'] = unevaluated_count
                else:
                    # requirement_idがない場合のフォールバック
                    job['candidate_count'] = 0
                    job['evaluated_count'] = 0
                    job['total_candidates'] = 0
                    job['unevaluated_count'] = 0
                    job['progress_fraction'] = "0/0"
                
            except Exception as e:
                print(f"Error processing job {job.get('id', 'unknown')}: {e}")
                # エラー時はデフォルト値を設定
                job['candidate_count'] = 0
                job['evaluated_count'] = 0
                job['total_candidates'] = 0
                job['unevaluated_count'] = 0
                job['progress_fraction'] = "0/0"
        
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
        "error_count": error_count,
        "base_path": "/admin"  # base_path変数を追加
    })

@app.get("/admin/jobs/{job_id}/details", response_class=HTMLResponse)
async def admin_job_details(job_id: str, request: Request, user: Optional[dict] = Depends(get_current_user_from_cookie)):
    """管理者 - ジョブ詳細"""
    if not user or user.get("role") != "admin":
        return RedirectResponse(url="/login?error=Unauthorized", status_code=303)
    
    try:
        from core.utils.supabase_client import get_supabase_client
        supabase = get_supabase_client()
        
        # ジョブ情報を取得（クライアント情報を含む）
        job_response = supabase.table('jobs').select(
            '*, client:clients(name)'
        ).eq('id', job_id).execute()
        
        if not job_response.data or len(job_response.data) == 0:
            return templates.TemplateResponse("admin/error.html", {
                "request": request, 
                "current_user": user,
                "error": "指定されたジョブが見つかりません"
            })
            
        job = job_response.data[0]
        
        # requirement情報を別途取得（requirement_idがtext型のため）
        if job.get('requirement_id'):
            try:
                # requirement_idを直接使用
                req_response = supabase.table('job_requirements').select('title').eq(
                    'id', job['requirement_id']
                ).execute()
                if req_response.data and len(req_response.data) > 0:
                    job['requirement'] = req_response.data[0]
                else:
                    job['requirement'] = {'title': 'N/A'}
            except Exception as req_error:
                print(f"Error fetching requirement: {req_error}")
                job['requirement'] = {'title': 'N/A'}
        
        # ステータス履歴を取得
        status_history = []
        try:
            history_response = supabase.table('job_status_history').select('*').eq(
                'job_id', job_id
            ).order('created_at', desc=False).execute()  # 古い順に表示
            status_history = history_response.data if history_response.data else []
        except Exception as history_error:
            print(f"Error fetching status history: {history_error}")
            # 履歴取得エラーは無視して続行
        
        # 処理済み候補者数を取得（完了したジョブの場合）
        processed_candidates = []
        if job.get('status') == 'completed':
            try:
                candidates_response = supabase.table('ai_evaluations').select(
                    'candidate_id, match_score, evaluation_result'
                ).eq('job_id', job_id).order('match_score', desc=True).execute()
                processed_candidates = candidates_response.data if candidates_response.data else []
            except Exception as eval_error:
                print(f"Error fetching evaluations: {eval_error}")
                # 評価取得エラーも無視して続行
        
        # 未評価候補者数を取得
        unevaluated_count = 0
        total_candidates_count = 0
        if job.get('requirement_id'):
            try:
                # 全候補者数を取得
                all_candidates_response = supabase.table('candidates').select(
                    'id', count='exact'
                ).eq('requirement_id', job['requirement_id']).execute()
                total_candidates_count = all_candidates_response.count or 0
                
                # 評価済み候補者IDを取得
                evaluated_response = supabase.table('ai_evaluations').select(
                    'candidate_id'
                ).eq('job_id', job_id).execute()
                evaluated_ids = [eval['candidate_id'] for eval in (evaluated_response.data or [])]
                
                # 未評価候補者数を計算
                evaluated_count = len(evaluated_ids)
                unevaluated_count = total_candidates_count - evaluated_count
                
                # ジョブに追加情報を設定
                job['total_candidates'] = total_candidates_count
                job['evaluated_count'] = evaluated_count
                job['unevaluated_count'] = unevaluated_count
                
            except Exception as count_error:
                print(f"Error counting candidates: {count_error}")
                job['total_candidates'] = 0
                job['evaluated_count'] = 0
                job['unevaluated_count'] = 0
        
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"Error fetching job details for job_id {job_id}: {e}")
        print(f"Traceback: {error_detail}")
        
        # エラーメッセージを詳細に
        error_message = f"ジョブ情報の取得に失敗しました (ID: {job_id})"
        if "relation" in str(e).lower():
            error_message += " - テーブル関連エラー"
        elif "connection" in str(e).lower():
            error_message += " - データベース接続エラー"
        
        return templates.TemplateResponse("admin/error.html", {
            "request": request, 
            "current_user": user,
            "error": error_message
        })
    
    return templates.TemplateResponse("admin/job_details.html", {
        "request": request, 
        "current_user": user,
        "job": job,
        "status_history": status_history,
        "processed_candidates": processed_candidates
    })

@app.get("/admin/jobs/new", response_class=HTMLResponse)
async def admin_jobs_new(request: Request, user: Optional[dict] = Depends(get_current_user_from_cookie)):
    """管理者 - 新規ジョブ作成"""
    if not user or user.get("role") != "admin":
        return RedirectResponse(url="/login?error=Unauthorized", status_code=303)
    
    try:
        from core.utils.supabase_client import get_supabase_client
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
    user: Optional[dict] = Depends(get_current_user_from_cookie)
):
    """管理者 - AIマッチングジョブ作成処理"""
    if not user or user.get("role") != "admin":
        return RedirectResponse(url="/login?error=Unauthorized", status_code=303)
    
    try:
        from core.utils.supabase_client import get_supabase_client
        from datetime import datetime
        import uuid
        
        supabase = get_supabase_client()
        
        # 次のjob_idを取得
        try:
            # 専用関数を使用
            sequence_response = supabase.rpc('get_next_job_id').execute()
            next_job_id = sequence_response.data if sequence_response.data else None
            
            if not next_job_id:
                raise Exception("Failed to get next job_id")
                
        except Exception as seq_error:
            print(f"Error with nextval: {seq_error}")
            # フォールバック: 最大値を取得して次の番号を生成
            try:
                max_response = supabase.table('jobs').select('job_id').like('job_id', 'job-%').order('job_id', desc=True).limit(1).execute()
                
                if max_response.data and len(max_response.data) > 0 and max_response.data[0].get('job_id'):
                    last_job_id = max_response.data[0]['job_id']
                    # job-001 形式から数値を抽出
                    if isinstance(last_job_id, str) and last_job_id.startswith('job-'):
                        last_num = int(last_job_id.split('-')[1])
                        next_num = last_num + 1
                    else:
                        next_num = 1
                else:
                    next_num = 1
                
                next_job_id = f"job-{str(next_num).zfill(3)}"
                    
            except Exception as fallback_error:
                print(f"Fallback also failed: {fallback_error}")
                # 最終手段: タイムスタンプベース
                import time
                next_job_id = f"job-{int(time.time()) % 10000:04d}"
        
        # ジョブデータを構築
        job_data = {
            "id": str(uuid.uuid4()),
            "job_id": next_job_id,  # 連番のjob_id
            "job_type": "ai_matching",  # AIマッチング固定
            "client_id": client_id,
            "requirement_id": requirement_id,
            "name": job_name,
            "status": "pending",  # 常にpendingで作成
            "priority": "normal",  # デフォルト優先度
            "created_by": user['id'],
            "created_at": datetime.utcnow().isoformat(),
            "parameters": {
                "data_source": "latest",  # デフォルト値
                "matching_threshold": "high",  # デフォルト値
                "output_sheets": True,  # デフォルト値
                "output_bigquery": True,  # デフォルト値
                "notify_completion": True  # デフォルト値
            }
        }
        
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
        import traceback
        traceback.print_exc()
        # エラーメッセージをURLセーフにエンコード
        import urllib.parse
        error_msg = urllib.parse.quote(str(e))
        return RedirectResponse(url=f"/admin/jobs/new?error=create_failed&message={error_msg}", status_code=303)

@app.post("/admin/api/jobs/{job_id}/execute")
async def admin_job_execute(job_id: str, request: Request, user: Optional[dict] = Depends(get_current_user_from_cookie)):
    """管理者 - ジョブ実行（直接実行）"""
    if not user or user.get("role") != "admin":
        return JSONResponse(status_code=403, content={"error": "Unauthorized"})
    
    try:
        # 直接AIマッチングサービスを呼び出し
        from webapp.services.ai_matching_service import ai_matching_service
        from core.utils.supabase_client import get_supabase_client
        from datetime import datetime
        import asyncio
        
        supabase = get_supabase_client()
        
        # ジョブの存在と権限確認
        job_response = supabase.table('jobs').select('*, client:clients(*)').eq('id', job_id).single().execute()
        
        if not job_response.data:
            return JSONResponse(status_code=404, content={"error": "ジョブが見つかりません"})
        
        job = job_response.data
        
        # 権限チェック（管理者またはジョブ作成者）
        if user['role'] != 'admin' and job.get('created_by') != user['id']:
            return JSONResponse(status_code=403, content={"error": "このジョブを実行する権限がありません"})
        
        # ジョブタイプの確認
        if job.get('job_type') != 'ai_matching':
            return JSONResponse(status_code=400, content={"error": "AIマッチングジョブではありません"})
        
        # ステータスの確認
        if job.get('status') not in ['pending', 'failed']:
            return JSONResponse(status_code=400, content={"error": "このジョブは既に実行中または完了しています"})
        
        # バックグラウンドでジョブを実行
        print(f"Starting job execution for job_id: {job_id}")
        asyncio.create_task(ai_matching_service.process_job(job_id))
        
        return JSONResponse(status_code=200, content={
            "success": True,
            "message": "ジョブの実行を開始しました",
            "job_id": job_id
        })
                
    except Exception as e:
        print(f"Error executing job: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": f"ジョブの実行開始に失敗しました: {str(e)}"})

@app.post("/admin/api/jobs/{job_id}/cancel")
async def admin_job_cancel(job_id: str, user: Optional[dict] = Depends(get_current_user_from_cookie)):
    """管理者 - ジョブ停止"""
    if not user or user.get("role") != "admin":
        return JSONResponse(status_code=403, content={"error": "Unauthorized"})
    
    try:
        from core.utils.supabase_client import get_supabase_client
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

@app.delete("/admin/api/jobs/{job_id}/delete")
async def admin_job_delete(job_id: str, user: Optional[dict] = Depends(get_current_user_from_cookie)):
    """管理者 - ジョブ削除"""
    if not user or user.get("role") != "admin":
        return JSONResponse(status_code=403, content={"error": "Unauthorized"})
    
    try:
        from core.utils.supabase_client import get_supabase_client
        
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
        from core.utils.supabase_client import get_supabase_client
        from core.services.candidate_counter import CandidateCounter
        
        supabase = get_supabase_client()
        candidate_counter = CandidateCounter()
        
        # ジョブ一覧を取得（クライアント情報と一緒に）
        jobs_response = supabase.table('jobs').select('*, client:clients(name)').order('created_at', desc=True).execute()
        jobs = jobs_response.data if jobs_response.data else []
        
        # クライアント名を展開と対象候補者数を追加（簡素化版）
        for job in jobs:
            if 'client' in job and job['client']:
                job['client_name'] = job['client']['name']
            else:
                job['client_name'] = 'N/A'
            
            try:
                # 基本的なcandidate_countのみ設定（既存ロジック）
                if job.get('status') == 'completed':
                    job['candidate_count'] = job.get('candidate_count', 0)
                elif job.get('status') in ['pending', 'ready', 'running']:
                    job_params = job.get('parameters', {})
                    client_id = job.get('client_id')
                    requirement_id = job.get('requirement_id')
                    
                    actual_count = candidate_counter.count_candidates(job_params, client_id, requirement_id)
                    if actual_count is not None:
                        job['candidate_count'] = actual_count
                    else:
                        job['candidate_count'] = candidate_counter.get_error_message()
                else:
                    job['candidate_count'] = 0
                
                # 分数表記は後で実装予定として、今は基本値を設定
                job['evaluated_count'] = 0
                job['total_candidates'] = 0
                job['progress_fraction'] = "0/0"
                
            except Exception as e:
                print(f"Error processing job {job.get('id', 'unknown')}: {e}")
                # エラー時はデフォルト値を設定
                job['candidate_count'] = 0
                job['evaluated_count'] = 0
                job['total_candidates'] = 0
                job['progress_fraction'] = "0/0"
        
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
        "error_count": error_count,
        "base_path": "/manager"  # base_path変数を追加
    })

@app.get("/manager/jobs/new", response_class=HTMLResponse)
async def manager_jobs_new(request: Request, user: Optional[dict] = Depends(get_current_user_from_cookie)):
    """マネージャー - 新規ジョブ作成"""
    if not user or user.get("role") != "manager":
        return RedirectResponse(url="/login?error=Unauthorized", status_code=303)
    
    try:
        from core.utils.supabase_client import get_supabase_client
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
        from core.utils.supabase_client import get_supabase_client
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

@app.post("/manager/api/jobs/{job_id}/execute")
async def manager_job_execute(job_id: str, user: Optional[dict] = Depends(get_current_user_from_cookie)):
    """マネージャー - ジョブ実行"""
    if not user or user.get("role") != "manager":
        return JSONResponse(status_code=403, content={"error": "Unauthorized"})
    
    try:
        from core.utils.supabase_client import get_supabase_client
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

@app.post("/manager/api/jobs/{job_id}/cancel")
async def manager_job_cancel(job_id: str, user: Optional[dict] = Depends(get_current_user_from_cookie)):
    """マネージャー - ジョブ停止"""
    if not user or user.get("role") != "manager":
        return JSONResponse(status_code=403, content={"error": "Unauthorized"})
    
    try:
        from core.utils.supabase_client import get_supabase_client
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

@app.delete("/manager/api/jobs/{job_id}/delete")
async def manager_job_delete(job_id: str, user: Optional[dict] = Depends(get_current_user_from_cookie)):
    """マネージャー - ジョブ削除"""
    if not user or user.get("role") != "manager":
        return JSONResponse(status_code=403, content={"error": "Unauthorized"})
    
    try:
        from core.utils.supabase_client import get_supabase_client
        
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
        from core.utils.supabase_client import get_supabase_client
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
        from core.utils.supabase_client import get_supabase_client
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
        from core.utils.supabase_client import get_supabase_client
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
        from core.utils.supabase_client import get_supabase_client
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
        from core.utils.supabase_client import get_supabase_client
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
        from core.utils.supabase_client import get_supabase_client
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
        from core.utils.supabase_client import get_supabase_client
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

# 評価画面
@app.get("/evaluations", response_class=HTMLResponse)
async def evaluations_list(
    request: Request,
    requirement_id: Optional[str] = None,
    has_feedback: Optional[str] = None,
    user: Optional[dict] = Depends(get_current_user_from_cookie)
):
    """評価一覧画面"""
    if not user:
        return RedirectResponse(url="/login?error=ログインが必要です", status_code=303)
    
    # adminまたはmanagerのみアクセス可能
    if user.get("role") not in ["admin", "manager"]:
        return templates.TemplateResponse("errors/403.html", {
            "request": request, 
            "message": "アクセス権限がありません", 
            "current_user": user
        }, status_code=403)
    
    supabase = get_supabase_client()
    
    # 評価データを取得
    query = supabase.table('ai_evaluations')\
        .select("""
            *,
            candidate:candidates(candidate_company, candidate_id),
            requirement:job_requirements(id, title)
        """)
    
    # フィルタ条件
    if requirement_id:
        query = query.eq('requirement_id', requirement_id)
    if has_feedback == 'true':
        query = query.not_.is_('client_evaluation', 'null')
    elif has_feedback == 'false':
        query = query.is_('client_evaluation', 'null')
    
    query = query.order('created_at', desc=True).limit(100)
    response = query.execute()
    
    # 要件リストを取得（フィルタ用）
    req_response = supabase.table('job_requirements')\
        .select('id, title')\
        .order('created_at', desc=True)\
        .execute()
    
    return templates.TemplateResponse("evaluations/list.html", {
        "request": request,
        "current_user": user,
        "evaluations": response.data if response.data else [],
        "requirements": req_response.data if req_response.data else []
    })

@app.get("/evaluations/{evaluation_id}", response_class=HTMLResponse)
async def evaluation_detail(
    request: Request,
    evaluation_id: str,
    user: Optional[dict] = Depends(get_current_user_from_cookie)
):
    """評価詳細画面"""
    if not user:
        return RedirectResponse(url="/login?error=ログインが必要です", status_code=303)
    
    # adminまたはmanagerのみアクセス可能
    if user.get("role") not in ["admin", "manager"]:
        return templates.TemplateResponse("errors/403.html", {
            "request": request, 
            "message": "アクセス権限がありません", 
            "current_user": user
        }, status_code=403)
    
    supabase = get_supabase_client()
    
    # 評価データを詳細情報と共に取得
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
        return templates.TemplateResponse("errors/404.html", {
            "request": request, 
            "message": "評価データが見つかりません", 
            "current_user": user
        }, status_code=404)
    
    return templates.TemplateResponse("evaluations/detail.html", {
        "request": request,
        "current_user": user,
        "evaluation": response.data
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