from fastapi import APIRouter, HTTPException, Depends, Request, Response, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordBearer
from typing import Optional
from pydantic import BaseModel, EmailStr
import jwt
from datetime import datetime, timedelta
import os

from ...utils.supabase_client import SupabaseAuth

router = APIRouter()

# JWT設定
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-here")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120 # 2時間に延長

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")

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
    print(f"get_current_user_from_cookie: access_token from cookie: {token}")
    if not token:
        print("get_current_user_from_cookie: No access_token found in cookie.")
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        print(f"get_current_user_from_cookie: Decoded payload: {payload}")
        if user_id is None:
            print("get_current_user_from_cookie: User ID is None in payload.")
            return None
        
        # ここではペイロードから直接ロールを取得する簡易版とします
        # 本来はDBに問い合わせるべきです
        return {"id": user_id, "email": payload.get("email"), "role": payload.get("role")}
    except jwt.PyJWTError as e:
        print(f"get_current_user_from_cookie: JWT Error: {e}")
        return None

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """現在のユーザーを取得"""
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
    except jwt.PyJWTError:
        raise credentials_exception
    
    user_info = await SupabaseAuth.get_current_user(token)
    if user_info is None:
        raise credentials_exception
    return user_info

@router.post("/login")
async def login(response: Response, email: str = Form(...), password: str = Form(...)):
    """ログインAPI（フォームデータ対応）"""
    result = await SupabaseAuth.sign_in(email, password)
    
    if not result["success"]:
        raise HTTPException(
            status_code=401,
            detail=result.get("error", "Invalid credentials")
        )
    
    # JWTトークンを作成
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": result["user"].id, "role": result["role"], "email": result["user"].email},
        expires_delta=access_token_expires
    )
    
    # ロールに基づいてリダイレクト先を決定
    if result["role"] == "admin":
        redirect_url = "/admin"
    else:
        redirect_url = "/user"
    
    # Cookieにトークンを設定してリダイレクト
    redirect_response = RedirectResponse(url=redirect_url, status_code=303)
    redirect_response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax"
    )
    
    return redirect_response

@router.post("/login/api", response_model=Token)
async def login_api(request: LoginRequest):
    """ログインAPI（JSON対応）"""
    result = await SupabaseAuth.sign_in(request.email, request.password)
    
    if not result["success"]:
        raise HTTPException(
            status_code=401,
            detail=result.get("error", "Invalid credentials")
        )
    
    # JWTトークンを作成
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": result["user"].id, "role": result["role"], "email": result["user"].email},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": result["role"]
    }

@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """ログアウトAPI"""
    await SupabaseAuth.sign_out()
    return {"message": "Successfully logged out"}

@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """現在のユーザー情報を取得"""
    return current_user

@router.post("/login-form")
async def login_form(
    email: str = Form(...),
    password: str = Form(...)
):
    """フォームベースのログイン（HTMLフォーム用）"""
    print(f"Login attempt for email: {email}")
    result = await SupabaseAuth.sign_in(email, password)
    
    print(f"Login result: {result}")
    
    if not result["success"]:
        return RedirectResponse(
            url="/login?error=Invalid credentials",
            status_code=303
        )
    
    # JWTトークンを作成
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": result["user"].id, "role": result["role"], "email": result["user"].email},
        expires_delta=access_token_expires
    )
    
    # リダイレクト先を決定
    redirect_url = f"/{result['role']}" if result['role'] in ['admin', 'user'] else "/"
    print(f"Redirecting to: {redirect_url}")
    
    # クッキーにトークンを設定
    response = RedirectResponse(
        url=redirect_url,
        status_code=303
    )
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,  # 開発環境ではFalseに
        samesite="lax"
    )
    
    return response