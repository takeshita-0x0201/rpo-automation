"""
Sync monitoring dashboard route
"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
import pathlib
from .auth import get_current_user_from_cookie

router = APIRouter()

# Sync monitor page
@router.get("/admin/sync-monitor", response_class=HTMLResponse)
async def sync_monitor_page(
    request: Request,
    user: Optional[dict] = Depends(get_current_user_from_cookie)
):
    """Pinecone同期モニターページ"""
    # 権限チェック
    if not user or user.get("role") != "admin":
        return RedirectResponse(url="/login?error=Unauthorized", status_code=303)
    
    base_dir = pathlib.Path(__file__).parent.parent
    templates = Jinja2Templates(directory=str(base_dir / "templates"))
    
    return templates.TemplateResponse("admin/sync_monitor.html", {
        "request": request,
        "current_user": user
    })