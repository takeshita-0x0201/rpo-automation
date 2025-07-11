import os
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from supabase import create_async_client, AsyncClient
from dotenv import load_dotenv
from fastapi.templating import Jinja2Templates
import pathlib
from typing import Optional
from pydantic import EmailStr

from src.web.routers.auth import get_current_user_from_cookie

# .envファイルから環境変数を読み込む
load_dotenv()

# Supabase URLとキー
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

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
    
    clients = []
    error_message = None
    try:
        # 非同期クライアントを関数内で初期化
        supabase_client: AsyncClient = await create_async_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        response = await supabase_client.table('clients').select("*").order('company_id').execute()
        if response.data:
            clients = response.data
    except Exception as e:
        print(f"Error fetching clients: {e}")
        error_message = f"データベースからのデータ取得中にエラーが発生しました: {e}"
    
    return templates.TemplateResponse("admin/clients.html", {"request": request, "clients": clients, "current_user": user, "error": error_message})

@router.get("/new", response_class=HTMLResponse)
async def new_client_page(request: Request, user: Optional[dict] = Depends(get_current_user_from_cookie)):
    """
    新規クライアント追加ページを表示します。
    """
    if not user or user.get("role") != "admin":
        return RedirectResponse(url="/login?error=Unauthorized", status_code=303)
    
    return templates.TemplateResponse("admin/new_client.html", {"request": request, "current_user": user})

@router.post("/new")
async def create_client(
    name: str = Form(...),
    industry: Optional[str] = Form(None),
    size: Optional[str] = Form(None),
    contact_person: Optional[str] = Form(None),
    contact_email: Optional[EmailStr] = Form(None),
    allows_direct_scraping: bool = Form(False),
    user: Optional[dict] = Depends(get_current_user_from_cookie)
):
    """
    新規クライアントをデータベースに登録します。
    """
    if not user or user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")

    # Generate company_id from name if not provided
    import re
    company_id = re.sub(r'[^a-zA-Z0-9]', '', name.lower())[:20]
    
    client_data = {
        "company_id": company_id,
        "name": name,
        "allows_direct_scraping": allows_direct_scraping
    }
    
    try:
        # 非同期クライアントを関数内で初期化 (書き込みにはSERVICE_KEYを使用)
        supabase_client: AsyncClient = await create_async_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        await supabase_client.table("clients").insert(client_data).execute()
    except Exception as e:
        print(f"Error creating client: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

    return RedirectResponse(url="/admin/clients", status_code=303)

@router.get("/api")
async def get_clients(user: Optional[dict] = Depends(get_current_user_from_cookie)):
    """
    クライアント企業の一覧をJSON形式で取得します。
    """
    if not user or user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
        
    # 非同期クライアントを関数内で初期化
    supabase_client: AsyncClient = await create_async_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    response = await supabase_client.table('clients').select("*").order('company_id').execute()
    return {"clients": response.data}

@router.get("/{client_id}/edit", response_class=HTMLResponse)
async def edit_client_page(client_id: str, request: Request, user: Optional[dict] = Depends(get_current_user_from_cookie)):
    """
    クライアント編集ページを表示します。
    """
    if not user or user.get("role") != "admin":
        return RedirectResponse(url="/login?error=Unauthorized", status_code=303)
    
    try:
        # 非同期クライアントを関数内で初期化
        supabase_client: AsyncClient = await create_async_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        response = await supabase_client.table('clients').select("*").eq('id', client_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Client not found")
        
        client = response.data[0]
        return templates.TemplateResponse("admin/edit_client.html", {"request": request, "client": client, "current_user": user})
    except Exception as e:
        print(f"Error fetching client: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.post("/{client_id}/edit")
async def update_client(
    client_id: str,
    request: Request,
    company_id: str = Form(...),
    name: str = Form(...),
    user: Optional[dict] = Depends(get_current_user_from_cookie)
):
    """
    クライアント情報を更新します。
    """
    if not user or user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    
    # Handle checkbox value
    form_data = await request.form()
    allows_direct_scraping = "allows_direct_scraping" in form_data
    
    update_data = {
        "company_id": company_id,
        "name": name,
        "allows_direct_scraping": allows_direct_scraping
    }
    
    try:
        # 非同期クライアントを関数内で初期化 (書き込みにはSERVICE_KEYを使用)
        supabase_client: AsyncClient = await create_async_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        await supabase_client.table("clients").update(update_data).eq('id', client_id).execute()
    except Exception as e:
        print(f"Error updating client: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
    return RedirectResponse(url="/admin/clients", status_code=303)

@router.post("/{client_id}/delete")
async def delete_client(
    client_id: str,
    user: Optional[dict] = Depends(get_current_user_from_cookie)
):
    """
    クライアントを削除します。
    """
    if not user or user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    
    try:
        # 非同期クライアントを関数内で初期化 (書き込みにはSERVICE_KEYを使用)
        supabase_client: AsyncClient = await create_async_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        await supabase_client.table("clients").delete().eq('id', client_id).execute()
    except Exception as e:
        print(f"Error deleting client: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
    return RedirectResponse(url="/admin/clients", status_code=303)