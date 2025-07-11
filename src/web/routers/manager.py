"""
マネージャー用のルーター
管理者と同じUIを使用するが、URLパスは/managerを使用
"""
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import Optional
from .auth import get_current_user_from_cookie

router = APIRouter(prefix="/manager")

async def get_current_manager_user(user: dict = Depends(get_current_user_from_cookie)) -> dict:
    if not user or user.get("role") != "manager":
        raise HTTPException(status_code=403, detail="Not authorized")
    return user

