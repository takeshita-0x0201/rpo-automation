"""
Chrome拡張機能用の認証ミドルウェア
"""
from fastapi import HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
import os
from typing import Optional

from core.utils.supabase_client import get_supabase_client

# JWT設定
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-here")
ALGORITHM = "HS256"

# HTTPBearerスキーム（auto_error=Falseでオプショナルに）
security = HTTPBearer(auto_error=False)

async def get_extension_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """拡張機能のトークンから現在のユーザーを取得"""
    if not credentials:
        print("Extension auth: No credentials provided")
        raise HTTPException(
            status_code=403,
            detail="認証情報が提供されていません"
        )
    
    token = credentials.credentials
    
    print(f"Extension auth: Token received: {token[:20]}..." if token else "No token")
    
    try:
        # トークンをデコード
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        print(f"Extension auth: Token decoded successfully, type: {payload.get('type')}")
        
        # トークンタイプの確認
        if payload.get("type") != "extension":
            print(f"Extension auth: Invalid token type: {payload.get('type')}")
            raise HTTPException(
                status_code=401,
                detail="無効なトークンタイプです"
            )
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="無効なトークンです"
            )
        
        # ユーザー情報を取得
        supabase = get_supabase_client()
        profile_result = supabase.table('profiles').select('*').eq('id', user_id).execute()
        
        if not profile_result.data:
            raise HTTPException(
                status_code=401,
                detail="ユーザーが見つかりません"
            )
        
        profile = profile_result.data[0]
        
        return {
            "id": user_id,
            "email": payload.get("email"),
            "full_name": profile.get('full_name', ''),
            "role": payload.get("role", profile.get('role', 'user'))
        }
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="トークンの有効期限が切れています"
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=401,
            detail="無効なトークンです"
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Extension auth error: {e}")
        raise HTTPException(
            status_code=500,
            detail="認証処理中にエラーが発生しました"
        )

async def require_extension_admin(user: dict = Depends(get_extension_user)):
    """管理者権限を要求"""
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail="この操作には管理者権限が必要です"
        )
    return user

async def require_extension_manager(user: dict = Depends(get_extension_user)):
    """マネージャー以上の権限を要求"""
    if user.get("role") not in ["admin", "manager"]:
        raise HTTPException(
            status_code=403,
            detail="この操作にはマネージャー以上の権限が必要です"
        )
    return user