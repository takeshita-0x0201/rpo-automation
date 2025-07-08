"""
RPO Automation WebApp Main Application
FastAPI-based web application entry point
"""

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
import uvicorn
import os
from typing import Optional

# ルーターのインポート
from src.web.routers import requirements, jobs, results, auth, clients, users

# FastAPIアプリケーションの初期化
app = FastAPI(
    title="RPO Automation System",
    description="AI・RPAツールを活用したRPO業務自動化システム",
    version="1.0.0"
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000"],
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
app.include_router(requirements.router, prefix="/api/requirements", tags=["requirements"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(results.router, prefix="/api/results", tags=["results"])
app.include_router(clients.router, prefix="/admin/clients", tags=["clients"])
app.include_router(users.router, prefix="/admin/users", tags=["users"])

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
@app.get("/admin/requirements", response_class=HTMLResponse)
async def admin_requirements(request: Request, user: Optional[dict] = Depends(get_current_user_from_cookie)):
    """管理者 - 採用要件管理"""
    if not user or user.get("role") != "admin":
        return RedirectResponse(url="/login?error=Unauthorized", status_code=303)
    # TODO: データベースから要件を取得
    requirements = []
    return templates.TemplateResponse("admin/requirements.html", {"request": request, "current_user": user, "requirements": requirements})

@app.get("/admin/jobs", response_class=HTMLResponse)
async def admin_jobs(request: Request, user: Optional[dict] = Depends(get_current_user_from_cookie)):
    """管理者 - ジョブ管理"""
    if not user or user.get("role") != "admin":
        return RedirectResponse(url="/login?error=Unauthorized", status_code=303)
    # TODO: ジョブデータを取得
    jobs = []
    return templates.TemplateResponse("admin/jobs.html", {"request": request, "current_user": user, "jobs": jobs})

@app.get("/admin/analytics", response_class=HTMLResponse)
async def admin_analytics(request: Request, user: Optional[dict] = Depends(get_current_user_from_cookie)):
    """管理者 - 分析レポート"""
    if not user or user.get("role") != "admin":
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
    # TODO: データベースから要件を取得
    requirements = []
    clients = []
    return templates.TemplateResponse("user/requirements.html", {
        "request": request, 
        "current_user": user, 
        "requirements": requirements,
        "clients": clients
    })

@app.get("/user/search", response_class=HTMLResponse)
async def user_search(request: Request, user: Optional[dict] = Depends(get_current_user_from_cookie)):
    """ユーザー - 候補者検索"""
    if not user:
        return RedirectResponse(url="/login?error=Unauthorized", status_code=303)
    # TODO: 要件リストを取得
    requirements = []
    selected_requirement_id = request.query_params.get("requirement_id")
    return templates.TemplateResponse("user/search.html", {
        "request": request, 
        "current_user": user, 
        "requirements": requirements,
        "selected_requirement_id": selected_requirement_id
    })

@app.get("/user/results", response_class=HTMLResponse)
async def user_results(request: Request, user: Optional[dict] = Depends(get_current_user_from_cookie)):
    """ユーザー - 検索結果"""
    if not user:
        return RedirectResponse(url="/login?error=Unauthorized", status_code=303)
    # TODO: 検索結果を取得
    candidates = []
    current_page = int(request.query_params.get("page", 1))
    total_pages = 1
    return templates.TemplateResponse("user/results.html", {
        "request": request, 
        "current_user": user, 
        "candidates": candidates,
        "current_page": current_page,
        "total_pages": total_pages
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