
import os
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from supabase import create_client, Client
from dotenv import load_dotenv
from fastapi.templating import Jinja2Templates
import pathlib

from typing import Optional
from src.web.routers.auth import get_current_user_from_cookie

# .envファイルから環境変数を読み込む
load_dotenv()

# Supabaseクライアントの初期化
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_ANON_KEY")
supabase: Client = create_client(url, key)

# APIRouterのインスタンスを作成
router = APIRouter()

# テンプレートの設定
base_dir = pathlib.Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(base_dir / "templates"))

@router.get("", response_class=HTMLResponse)
async def list_clients_page(request: Request, user: Optional[dict] = Depends(get_current_user_from_cookie)):
    """
    クライアント企業の一覧をHTMLページとして表示します。
    """
    if not user or user.get("role") != "admin":
        return RedirectResponse(url="/login?error=Unauthorized", status_code=303)
    
    # Supabaseからクライアント一覧を取得
    response = supabase.table('clients').select("*").order('created_at', desc=True).execute()
    clients = response.data
    
    return templates.TemplateResponse("clients.html", {"request": request, "clients": clients, "user": user})

@router.get("/api")
async def get_clients():
    """
    クライアント企業の一覧をJSON形式で取得します。
    """
    response = supabase.table('clients').select("*").order('created_at', desc=True).execute()
    return {"clients": response.data}
