"""
共通の依存関係とデコレーター
"""
from fastapi import HTTPException, Request, Depends
from typing import Optional
from functools import wraps
import jwt
import os

from core.utils.supabase_client import get_supabase_client

# JWT設定
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"

async def get_current_user(request: Request) -> Optional[dict]:
    """現在のユーザーを取得"""
    # リクエストのstateからユーザー情報を取得
    if hasattr(request.state, 'user'):
        return request.state.user
    
    # Cookieからアクセストークンを取得
    token = request.cookies.get("access_token")
    if not token:
        print(f"[Auth Debug] No access_token cookie found. Available cookies: {list(request.cookies.keys())}")
        return None
    
    try:
        print(f"[Auth Debug] Found access_token cookie, attempting to decode JWT...")
        # JWTトークンをデコード
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            print(f"[Auth Debug] No user ID in JWT payload")
            return None
        
        print(f"[Auth Debug] JWT decoded successfully. User: {payload.get('email')}")
        
        # ユーザー情報を返す
        return {
            "id": user_id,
            "email": payload.get("email"),
            "role": payload.get("role", "user"),
            "full_name": payload.get("full_name", "")
        }
    except jwt.ExpiredSignatureError:
        print(f"[Auth Debug] JWT token expired")
        return None
    except jwt.JWTError as e:
        print(f"[Auth Debug] JWT decode error: {type(e).__name__}: {str(e)}")
        return None
    except Exception as e:
        print(f"[Auth Debug] Unexpected error: {type(e).__name__}: {str(e)}")
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
        raise HTTPException(status_code=401, detail="Unauthorized - Please login")
    
    # リクエストのstateにユーザー情報を保存
    request.state.user = user
    
    return user