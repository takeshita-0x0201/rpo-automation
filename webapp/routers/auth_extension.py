"""
Chrome拡張機能用の認証エンドポイント
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import jwt
import os

from core.utils.supabase_client import SupabaseAuth, get_supabase_client, get_user_role

router = APIRouter(prefix="/api/auth/extension", tags=["extension-auth"])

# JWT設定（auth.pyと同じ設定を使用）
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-here")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 拡張機能用は24時間

class ExtensionLoginRequest(BaseModel):
    email: EmailStr
    password: str

class ExtensionLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]

class ExtensionUserInfo(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    role: str

def create_extension_token(data: dict, expires_delta: Optional[timedelta] = None):
    """拡張機能用のJWTトークンを作成"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=30)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

@router.post("/login", response_model=ExtensionLoginResponse)
async def extension_login(request: ExtensionLoginRequest):
    """Chrome拡張機能用のログインエンドポイント"""
    try:
        # Supabaseで認証
        result = await SupabaseAuth.sign_in(request.email, request.password)
        
        if not result["success"]:
            raise HTTPException(
                status_code=401,
                detail=result.get("error", "認証に失敗しました")
            )
        
        user = result["user"]
        role = result["role"]
        
        # プロフィール情報を取得
        supabase = get_supabase_client()
        profile_result = supabase.table('profiles').select('*').eq('id', user.id).execute()
        
        if profile_result.data and len(profile_result.data) > 0:
            profile = profile_result.data[0]
            full_name = profile.get('full_name', '')
        else:
            full_name = ''
        
        # JWTトークンを作成
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_extension_token(
            data={
                "sub": user.id,
                "email": user.email,
                "role": role,
                "type": "extension"  # 拡張機能からのトークンを識別
            },
            expires_delta=access_token_expires
        )
        
        # ユーザー情報を整形
        user_info = {
            "id": user.id,
            "email": user.email,
            "full_name": full_name,
            "role": role
        }
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": user_info,
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60  # 秒単位で返す
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Extension login error: {e}")
        raise HTTPException(
            status_code=500,
            detail="ログイン処理中にエラーが発生しました"
        )

@router.get("/verify")
async def verify_extension_token(token: str):
    """拡張機能のトークンを検証"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # トークンタイプの確認
        if payload.get("type") != "extension":
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
            "valid": True,
            "user": {
                "id": user_id,
                "email": payload.get("email"),
                "full_name": profile.get('full_name', ''),
                "role": payload.get("role")
            }
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
        print(f"Token verification error: {e}")
        raise HTTPException(
            status_code=500,
            detail="トークン検証中にエラーが発生しました"
        )

@router.post("/refresh")
async def refresh_extension_token(token: str):
    """拡張機能のトークンをリフレッシュ"""
    try:
        # 既存のトークンを検証（期限切れでも内容は取得）
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": False})
        except jwt.PyJWTError:
            raise HTTPException(
                status_code=401,
                detail="無効なトークンです"
            )
        
        # トークンタイプの確認
        if payload.get("type") != "extension":
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
        
        # ユーザーが存在するか確認
        supabase = get_supabase_client()
        profile_result = supabase.table('profiles').select('id, role').eq('id', user_id).execute()
        
        if not profile_result.data:
            raise HTTPException(
                status_code=401,
                detail="ユーザーが見つかりません"
            )
        
        # 新しいトークンを生成
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        new_token = create_extension_token(
            data={
                "sub": user_id,
                "email": payload.get("email"),
                "role": profile_result.data[0]["role"],
                "type": "extension"
            },
            expires_delta=access_token_expires
        )
        
        return {
            "access_token": new_token,
            "token_type": "bearer"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=500,
            detail="トークンリフレッシュ中にエラーが発生しました"
        )