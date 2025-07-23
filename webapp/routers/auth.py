from fastapi import APIRouter, HTTPException, Depends, Request, Response, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from pydantic import BaseModel, EmailStr
import jwt
from datetime import datetime, timedelta
import os

from core.utils.supabase_client import SupabaseAuth

router = APIRouter()

# JWT設定
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-here")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120 # 2時間に延長

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")
http_bearer = HTTPBearer()

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    role: Optional[str] = None

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """JWTトークンを作成"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user_from_cookie(request: Request) -> Optional[dict]:
    """Cookieからアクセストークンを取得し、現在のユーザーを返す"""
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
        # ユーザー情報を返す
        return {
            "id": user_id,
            "email": payload.get("email"),
            "role": payload.get("role"),
            "full_name": payload.get("full_name")
        }
    except jwt.ExpiredSignatureError:
        return None
    except jwt.JWTError:
        return None

async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """APIアクセス用の認証"""
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        return {
            "id": user_id,
            "email": payload.get("email"),
            "role": payload.get("role"),
            "full_name": payload.get("full_name")
        }
    except jwt.JWTError:
        raise credentials_exception

async def get_api_key_user(credentials: HTTPAuthorizationCredentials = Depends(http_bearer)) -> dict:
    """API Key認証（GASからのアクセス用）"""
    api_key = credentials.credentials
    
    # 環境変数からAPI Keyを取得
    valid_api_key = os.getenv("GAS_API_KEY", "your-gas-api-key")
    
    if api_key != valid_api_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # GAS用の特別なユーザーオブジェクトを返す
    return {
        "id": "gas-service",
        "email": "gas@rpo-automation.local",
        "role": "service",
        "full_name": "Google Apps Script Service"
    }

@router.post("/login", response_model=Token)
async def login(request: LoginRequest, response: Response):
    """メールアドレスとパスワードでログイン"""
    try:
        # Supabaseで認証
        auth = SupabaseAuth()
        user_data = await auth.sign_in(request.email, request.password)
        
        print(f"Auth response: {user_data}")  # デバッグ用
        
        if not user_data or not user_data.get("success"):
            raise HTTPException(status_code=401, detail=user_data.get("error", "Invalid email or password") if user_data else "Invalid email or password")
        
        user = user_data.get("user")
        if not user:
            raise HTTPException(status_code=401, detail="User data not found")
        
        # JWTトークンを作成
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={
                "sub": user.id if hasattr(user, 'id') else user.get("id"),
                "email": user.email if hasattr(user, 'email') else user.get("email"),
                "role": user_data.get("role", "user"),
                "full_name": getattr(user, 'user_metadata', {}).get('full_name', '') if hasattr(user, 'user_metadata') else ""
            },
            expires_delta=access_token_expires
        )
        
        # Cookieにトークンを設定
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            secure=True,
            samesite="lax"
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "role": user_data.get("role", "user")
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

@router.post("/logout")
async def logout(response: Response):
    """ログアウト"""
    response.delete_cookie("access_token")
    return {"message": "ログアウトしました"}

@router.post("/login-form", response_class=HTMLResponse)
async def login_form(
    request: Request,
    response: Response,
    email: str = Form(...),
    password: str = Form(...)
):
    """フォームからのログイン処理"""
    try:
        # Supabaseで認証
        auth = SupabaseAuth()
        user_data = await auth.sign_in(email, password)
        
        print(f"Form auth response: {user_data}")  # デバッグ用
        
        if not user_data or not user_data.get("success"):
            error_msg = user_data.get("error", "Authentication failed") if user_data else "Invalid credentials"
            return RedirectResponse(url=f"/login?error={error_msg}", status_code=303)
        
        user = user_data.get("user")
        if not user:
            return RedirectResponse(url="/login?error=User data not found", status_code=303)
        
        # JWTトークンを作成
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={
                "sub": user.id if hasattr(user, 'id') else user.get("id"),
                "email": user.email if hasattr(user, 'email') else user.get("email"),
                "role": user_data.get("role", "user"),
                "full_name": getattr(user, 'user_metadata', {}).get('full_name', '') if hasattr(user, 'user_metadata') else ""
            },
            expires_delta=access_token_expires
        )
        
        # リダイレクト先を決定
        if user_data.get("role") == "admin":
            redirect_url = "/admin"
        elif user_data.get("role") == "manager":
            redirect_url = "/manager"
        else:
            redirect_url = "/user"
        
        # Cookieを設定してリダイレクト
        redirect_response = RedirectResponse(url=redirect_url, status_code=303)
        redirect_response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            secure=True,
            samesite="lax"
        )
        
        return redirect_response
        
    except Exception as e:
        print(f"Login error: {e}")
        return RedirectResponse(url="/login?error=Authentication failed", status_code=303)

@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """現在のユーザー情報を取得"""
    return current_user