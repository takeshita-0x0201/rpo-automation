"""
RPO Automation WebApp Main Application
FastAPI-based web application entry point
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
import uvicorn
import os
from typing import Optional

# ルーターのインポート
from src.web.routers import requirements, jobs, results, auth

# FastAPIアプリケーションの初期化
app = FastAPI(
    title="RPO Automation System",
    description="AI・RPAツールを活用したRPO業務自動化システム",
    version="1.0.0"
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://localhost:3000"],
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

# 認証チェック用の依存関係
from src.web.routers.auth import get_current_user

# ルートエンドポイント
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """メインページ（ログインページへリダイレクト）"""
    return RedirectResponse(url="/login", status_code=303)

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """ログインページ"""
    error = request.query_params.get("error")
    return templates.TemplateResponse("login.html", {"request": request, "error": error})

@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    """管理者ダッシュボード"""
    # TODO: 認証チェックとロールチェックを実装
    return templates.TemplateResponse("admin_dashboard.html", {"request": request})

@app.get("/user", response_class=HTMLResponse)
async def user_dashboard(request: Request):
    """ユーザーダッシュボード"""
    # TODO: 認証チェックを実装
    return templates.TemplateResponse("user_dashboard.html", {"request": request})

@app.get("/logout")
async def logout(request: Request):
    """ログアウト"""
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("access_token")
    return response

# ヘルスチェックエンドポイント
@app.get("/health")
async def health_check():
    """ヘルスチェック"""
    return {"status": "healthy", "service": "rpo-automation-webapp"}

# エラーハンドラー
@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """404エラーハンドラー"""
    return templates.TemplateResponse("404.html", {"request": request}, status_code=404)

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: HTTPException):
    """500エラーハンドラー"""
    return templates.TemplateResponse("500.html", {"request": request}, status_code=500)

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