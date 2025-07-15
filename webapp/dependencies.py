"""
共通の依存関係とデコレーター
"""
from fastapi import HTTPException, Request, Depends
from typing import Optional
from functools import wraps

from core.utils.supabase_client import get_supabase_client

async def get_current_user(request: Request) -> Optional[dict]:
    """現在のユーザーを取得"""
    # リクエストのstateからユーザー情報を取得
    if hasattr(request.state, 'user'):
        return request.state.user
    
    # Cookieからアクセストークンを取得
    access_token = request.cookies.get("access_token")
    if not access_token:
        return None
    
    try:
        supabase = get_supabase_client()
        user_response = supabase.auth.get_user(access_token)
        
        if user_response.user:
            # ユーザーの役職を取得
            profile_result = supabase.table('profiles').select('*').eq('id', user_response.user.id).execute()
            
            if profile_result.data and len(profile_result.data) > 0:
                profile = profile_result.data[0]
                return {
                    "id": user_response.user.id,
                    "email": user_response.user.email,
                    "full_name": profile.get('full_name'),
                    "role": profile.get('role', 'user'),
                    "department": profile.get('department')
                }
            else:
                return {
                    "id": user_response.user.id,
                    "email": user_response.user.email,
                    "role": "user"
                }
    except Exception as e:
        return None

async def admin_only(request: Request):
    """管理者のみアクセス可能"""
    user = await get_current_user(request)
    
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    if user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # リクエストのstateにユーザー情報を保存
    request.state.user = user
    
    return user

async def manager_or_admin(request: Request):
    """マネージャーまたは管理者のみアクセス可能"""
    user = await get_current_user(request)
    
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    if user.get('role') not in ['admin', 'manager']:
        raise HTTPException(status_code=403, detail="Manager or admin access required")
    
    # リクエストのstateにユーザー情報を保存
    request.state.user = user
    
    return user

async def authenticated_user(request: Request):
    """認証済みユーザーのみアクセス可能"""
    user = await get_current_user(request)
    
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # リクエストのstateにユーザー情報を保存
    request.state.user = user
    
    return user