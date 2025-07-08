"""
ユーザー管理用のルーター
管理者のみがアクセス可能
"""
from fastapi import APIRouter, HTTPException, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional, List
from datetime import datetime
import uuid
from pydantic import BaseModel, EmailStr, constr
from enum import Enum

from ...utils.supabase_client import get_supabase_client
from .auth import get_current_user_from_cookie

router = APIRouter()
templates = Jinja2Templates(directory="src/web/templates")

class UserRole(str, Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    OPERATOR = "operator"

class UserCreate(BaseModel):
    email: EmailStr
    password: constr(min_length=6)
    full_name: str
    role: UserRole
    department: Optional[str] = None

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    department: Optional[str] = None

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str]
    role: Optional[str]
    department: Optional[str]
    created_at: datetime
    updated_at: datetime

@router.get("/", response_class=HTMLResponse)
async def list_users(request: Request, current_user: dict = Depends(get_current_user_from_cookie)):
    """ユーザー一覧を表示"""
    # 管理者権限チェック
    if not current_user or current_user.get("role") != "admin":
        return RedirectResponse(url="/login?error=Unauthorized", status_code=303)
    
    try:
        supabase = get_supabase_client()
        
        # プロファイル情報を取得
        profiles_result = supabase.table('profiles').select('*').execute()
        profiles = profiles_result.data
        
        # auth.usersの情報も取得（メールアドレスのため）
        # 注意: これは管理者APIキーが必要
        try:
            users_result = supabase.auth.admin.list_users()
            
            users_dict = {}
            
            # 様々な形式に対応
            if hasattr(users_result, 'users'):
                # users_result.users の形式
                for user in users_result.users:
                    users_dict[user.id] = user.email
            elif isinstance(users_result, tuple) and len(users_result) > 0:
                # タプルの形式
                if hasattr(users_result[0], 'users'):
                    for user in users_result[0].users:
                        users_dict[user.id] = user.email
            elif isinstance(users_result, list):
                # リストの形式
                for user in users_result:
                    if hasattr(user, 'id') and hasattr(user, 'email'):
                        users_dict[user.id] = user.email
            
            # users_dictが空の場合、個別に取得を試みる
            if not users_dict:
                for profile in profiles:
                    try:
                        user_info = supabase.auth.admin.get_user_by_id(profile['id'])
                        if user_info and hasattr(user_info, 'user') and user_info.user:
                            profile['email'] = user_info.user.email
                        else:
                            profile['email'] = 'メールアドレス取得エラー'
                    except Exception as user_error:
                        profile['email'] = 'N/A'
            else:
                for profile in profiles:
                    profile['email'] = users_dict.get(profile['id'], 'メールアドレス取得エラー')
                
        except Exception as e:
            # エラーが発生した場合は、メールアドレスを取得できないので空のdictを使用
            for profile in profiles:
                profile['email'] = 'N/A'
        
        return templates.TemplateResponse(
            "admin/users.html",
            {
                "request": request,
                "users": profiles,
                "current_user": current_user
            }
        )
    except Exception as e:
        print(f"Error listing users: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/new", response_class=HTMLResponse)
async def new_user_form(request: Request, current_user: dict = Depends(get_current_user_from_cookie)):
    """新規ユーザー作成フォームを表示"""
    # 管理者権限チェック
    if not current_user or current_user.get("role") != "admin":
        return RedirectResponse(url="/login?error=Unauthorized", status_code=303)
    
    return templates.TemplateResponse(
        "admin/new_user.html",
        {
            "request": request,
            "roles": [role.value for role in UserRole],
            "current_user": current_user
        }
    )

@router.post("/")
async def create_user(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    full_name: Optional[str] = Form(None),
    department: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user_from_cookie)
):
    """新規ユーザーを作成"""
    # 管理者権限チェック
    if not current_user or current_user.get("role") != "admin":
        return RedirectResponse(url="/login?error=Unauthorized", status_code=303)
    
    try:
        supabase = get_supabase_client()
        
        # Supabase Authでユーザーを作成
        auth_result = supabase.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": True
        })
        
        if not auth_result.user:
            raise HTTPException(status_code=400, detail="Failed to create user")
        
        user_id = auth_result.user.id
        
        # プロファイルを作成
        profile_data = {
            "id": user_id,
            "email": email,  # メールアドレスを追加
            "role": role,
            "status": "active"
        }
            
        print(f"Creating profile with data: {profile_data}")
        
        try:
            profile_result = supabase.table('profiles').insert(profile_data).execute()
            print(f"Profile creation result: {profile_result}")
            
            if not profile_result.data:
                # ユーザー作成に失敗したらauth userも削除
                supabase.auth.admin.delete_user(user_id)
                raise HTTPException(status_code=400, detail="Failed to create profile")
        except Exception as profile_error:
            print(f"Profile creation error: {profile_error}")
            # ユーザー作成に失敗したらauth userも削除
            supabase.auth.admin.delete_user(user_id)
            raise HTTPException(status_code=400, detail=f"Failed to create profile: {str(profile_error)}")
        
        return RedirectResponse(url="/admin/users", status_code=303)
        
    except Exception as e:
        print(f"Error creating user: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{user_id}/edit", response_class=HTMLResponse)
async def edit_user_form(request: Request, user_id: str, current_user: dict = Depends(get_current_user_from_cookie)):
    """ユーザー編集フォームを表示"""
    # 管理者権限チェック
    if not current_user or current_user.get("role") != "admin":
        return RedirectResponse(url="/login?error=Unauthorized", status_code=303)
    
    try:
        supabase = get_supabase_client()
        
        # プロファイル情報を取得
        profile_result = supabase.table('profiles').select('*').eq('id', user_id).execute()
        
        if not profile_result.data:
            raise HTTPException(status_code=404, detail="User not found")
        
        profile = profile_result.data[0]
        
        # メールアドレスを取得
        user_result = supabase.auth.admin.get_user_by_id(user_id)
        if user_result.user:
            profile['email'] = user_result.user.email
        
        return templates.TemplateResponse(
            "admin/edit_user.html",
            {
                "request": request,
                "user": profile,
                "roles": [role.value for role in UserRole],
                "current_user": current_user
            }
        )
    except Exception as e:
        print(f"Error getting user for edit: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{user_id}/edit")
async def update_user(
    request: Request,
    user_id: str,
    role: str = Form(...),
    current_user: dict = Depends(get_current_user_from_cookie)
):
    """ユーザー情報を更新"""
    # 管理者権限チェック
    if not current_user or current_user.get("role") != "admin":
        return RedirectResponse(url="/login?error=Unauthorized", status_code=303)
    
    try:
        supabase = get_supabase_client()
        
        # プロファイルを更新
        update_data = {
            "role": role,
            "updated_at": datetime.now().isoformat()
        }
        
        result = supabase.table('profiles').update(update_data).eq('id', user_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="User not found")
        
        return RedirectResponse(url="/admin/users", status_code=303)
        
    except Exception as e:
        print(f"Error updating user: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{user_id}/activate")
async def activate_user(request: Request, user_id: str, current_user: dict = Depends(get_current_user_from_cookie)):
    """ユーザーを有効化"""
    # 管理者権限チェック
    if not current_user or current_user.get("role") != "admin":
        return RedirectResponse(url="/login?error=Unauthorized", status_code=303)
    
    try:
        supabase = get_supabase_client()
        
        # 自分自身は無効化できない
        if current_user.get("id") == user_id:
            raise HTTPException(status_code=400, detail="Cannot deactivate yourself")
        
        # プロファイルのstatusを更新
        update_data = {
            "status": "active",
            "updated_at": datetime.now().isoformat()
        }
        
        result = supabase.table('profiles').update(update_data).eq('id', user_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="User not found")
        
        return RedirectResponse(url="/admin/users", status_code=303)
        
    except Exception as e:
        print(f"Error activating user: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{user_id}/deactivate")
async def deactivate_user(request: Request, user_id: str, current_user: dict = Depends(get_current_user_from_cookie)):
    """ユーザーを無効化"""
    # 管理者権限チェック
    if not current_user or current_user.get("role") != "admin":
        return RedirectResponse(url="/login?error=Unauthorized", status_code=303)
    
    try:
        supabase = get_supabase_client()
        
        # 自分自身は無効化できない
        if current_user.get("id") == user_id:
            raise HTTPException(status_code=400, detail="Cannot deactivate yourself")
        
        # プロファイルのstatusを更新
        update_data = {
            "status": "inactive",
            "updated_at": datetime.now().isoformat()
        }
        
        result = supabase.table('profiles').update(update_data).eq('id', user_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="User not found")
        
        return RedirectResponse(url="/admin/users", status_code=303)
        
    except Exception as e:
        print(f"Error deactivating user: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{user_id}/delete")
async def delete_user(request: Request, user_id: str, current_user: dict = Depends(get_current_user_from_cookie)):
    """ユーザーを削除"""
    # 管理者権限チェック
    if not current_user or current_user.get("role") != "admin":
        return RedirectResponse(url="/login?error=Unauthorized", status_code=303)
    
    try:
        supabase = get_supabase_client()
        
        # 自分自身は削除できない
        if current_user.get("id") == user_id:
            raise HTTPException(status_code=400, detail="Cannot delete yourself")
        
        # プロファイルを削除（カスケードでauth userも削除される設定の場合）
        # まずプロファイルを削除
        profile_result = supabase.table('profiles').delete().eq('id', user_id).execute()
        
        # Supabase Authからもユーザーを削除
        auth_result = supabase.auth.admin.delete_user(user_id)
        
        return RedirectResponse(url="/admin/users", status_code=303)
        
    except Exception as e:
        print(f"Error deleting user: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# API エンドポイント（JSON レスポンス）
@router.get("/api", response_model=List[UserResponse])
async def list_users_api(current_user: dict = Depends(get_current_user_from_cookie)):
    """ユーザー一覧をJSON形式で取得"""
    # 管理者権限チェック
    if not current_user or current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        supabase = get_supabase_client()
        result = supabase.table('profiles').select('*').execute()
        return result.data
    except Exception as e:
        print(f"Error listing users: {e}")
        raise HTTPException(status_code=500, detail=str(e))