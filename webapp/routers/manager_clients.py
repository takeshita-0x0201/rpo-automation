import os
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from supabase import create_async_client, AsyncClient
from dotenv import load_dotenv
from fastapi.templating import Jinja2Templates
import pathlib
from typing import Optional
from pydantic import EmailStr

from .auth import get_current_user_from_cookie

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
    if not user or user.get("role") != "manager":
        return RedirectResponse(url="/login?error=Unauthorized", status_code=303)
    
    clients = []
    error_message = None
    try:
        # 非同期クライアントを関数内で初期化
        supabase_client: AsyncClient = await create_async_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        # 媒体情報も一緒に取得
        response = await supabase_client.table('clients').select("*, media_platform:media_platforms(display_name)").order('company_id').execute()
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
    if not user or user.get("role") != "manager":
        return RedirectResponse(url="/login?error=Unauthorized", status_code=303)
    
    try:
        # 非同期クライアントを関数内で初期化
        supabase_client: AsyncClient = await create_async_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        # 媒体プラットフォーム一覧を取得
        platforms_response = await supabase_client.table('media_platforms').select("*").eq('is_active', True).order('sort_order').execute()
        media_platforms = platforms_response.data if platforms_response.data else []
    except Exception as e:
        print(f"Error fetching media platforms: {e}")
        media_platforms = []
    
    return templates.TemplateResponse("admin/new_client.html", {
        "request": request, 
        "current_user": user,
        "media_platforms": media_platforms
    })

@router.post("/new")
async def create_client(
    name: str = Form(...),
    media_platform_id: str = Form(...),
    user: Optional[dict] = Depends(get_current_user_from_cookie)
):
    """
    新規クライアントをデータベースに登録します。
    """
    if not user or user.get("role") != "manager":
        raise HTTPException(status_code=403, detail="Forbidden")

    try:
        # 非同期クライアントを関数内で初期化 (書き込みにはSERVICE_KEYを使用)
        supabase_client: AsyncClient = await create_async_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        
        # company_idを生成
        try:
            # RPC関数を使用
            company_id_response = await supabase_client.rpc('generate_company_id').execute()
            company_id = company_id_response.data if company_id_response.data else None
            
            if not company_id:
                raise Exception("Failed to generate company_id")
                
        except Exception as gen_error:
            print(f"Error generating company_id with RPC: {gen_error}")
            # フォールバック: 最大値を取得して次の番号を生成
            try:
                max_response = await supabase_client.table('clients').select('company_id').like('company_id', 'comp-%').order('company_id', desc=True).limit(1).execute()
                
                if max_response.data and len(max_response.data) > 0:
                    last_id = max_response.data[0]['company_id']
                    # comp-001 形式から数値を抽出
                    last_num = int(last_id.split('-')[1])
                    next_num = last_num + 1
                else:
                    next_num = 1
                
                company_id = f"comp-{str(next_num).zfill(3)}"
            except Exception as fallback_error:
                print(f"Fallback also failed: {fallback_error}")
                # 最終手段: タイムスタンプベース
                import time
                company_id = f"comp-{int(time.time()) % 10000:04d}"
        
        client_data = {
            "company_id": company_id,
            "name": name,
            "media_platform_id": media_platform_id,
            "is_active": True
        }
        
        response = await supabase_client.table("clients").insert(client_data).execute()
        
        if not response.data:
            raise Exception("Failed to create client")
            
    except Exception as e:
        print(f"Error creating client: {e}")
        import urllib.parse
        error_msg = urllib.parse.quote(str(e))
        return RedirectResponse(url=f"/manager/clients/new?error=create_failed&message={error_msg}", status_code=303)

    return RedirectResponse(url="/manager/clients?success=created", status_code=303)

@router.get("/api")
async def get_clients(user: Optional[dict] = Depends(get_current_user_from_cookie)):
    """
    クライアント企業の一覧をJSON形式で取得します。
    """
    if not user or user.get("role") != "manager":
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
    if not user or user.get("role") != "manager":
        return RedirectResponse(url="/login?error=Unauthorized", status_code=303)
    
    try:
        # 非同期クライアントを関数内で初期化
        supabase_client: AsyncClient = await create_async_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        
        # クライアント情報を取得
        response = await supabase_client.table('clients').select("*").eq('id', client_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Client not found")
        
        client = response.data[0]
        
        # 媒体プラットフォーム一覧を取得
        platforms_response = await supabase_client.table('media_platforms').select("*").eq('is_active', True).order('sort_order').execute()
        media_platforms = platforms_response.data if platforms_response.data else []
        
        return templates.TemplateResponse("admin/edit_client.html", {
            "request": request, 
            "client": client, 
            "media_platforms": media_platforms,
            "current_user": user
        })
    except Exception as e:
        print(f"Error fetching client: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.post("/{client_id}/edit")
async def update_client(
    client_id: str,
    request: Request,
    company_id: str = Form(...),
    name: str = Form(...),
    media_platform_id: str = Form(...),
    user: Optional[dict] = Depends(get_current_user_from_cookie)
):
    """
    クライアント情報を更新します。
    """
    if not user or user.get("role") != "manager":
        raise HTTPException(status_code=403, detail="Forbidden")
    
    update_data = {
        "company_id": company_id,
        "name": name,
        "media_platform_id": media_platform_id
    }
    
    try:
        # 非同期クライアントを関数内で初期化 (書き込みにはSERVICE_KEYを使用)
        supabase_client: AsyncClient = await create_async_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        await supabase_client.table("clients").update(update_data).eq('id', client_id).execute()
    except Exception as e:
        print(f"Error updating client: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
    return RedirectResponse(url="/manager/clients", status_code=303)

@router.post("/{client_id}/delete")
async def delete_client(
    client_id: str,
    user: Optional[dict] = Depends(get_current_user_from_cookie)
):
    """
    クライアントを削除します。
    """
    if not user or user.get("role") != "manager":
        raise HTTPException(status_code=403, detail="Forbidden")
    
    try:
        # 非同期クライアントを関数内で初期化 (書き込みにはSERVICE_KEYを使用)
        supabase_client: AsyncClient = await create_async_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        
        # まず削除対象が存在するか確認
        check_response = await supabase_client.table("clients").select('id').eq('id', client_id).execute()
        if not check_response.data:
            return RedirectResponse(url="/manager/clients?error=not_found", status_code=303)
        
        # 削除実行
        response = await supabase_client.table("clients").delete().eq('id', client_id).execute()
        
        # 削除結果の確認
        if not response.data:
            raise Exception("削除に失敗しました")
            
    except Exception as e:
        error_msg = str(e)
        if "violates foreign key constraint" in error_msg:
            # 外部キー制約エラー
            print(f"Foreign key constraint error deleting client: {error_msg}")
            return RedirectResponse(url="/manager/clients?error=has_related_data", status_code=303)
        else:
            # その他のエラー
            print(f"Error deleting client: {error_msg}")
            return RedirectResponse(url="/manager/clients?error=delete_failed", status_code=303)
    
    return RedirectResponse(url="/manager/clients?success=deleted", status_code=303)