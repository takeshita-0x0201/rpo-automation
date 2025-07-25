"""
管理者用媒体プラットフォーム管理
"""
from fastapi import APIRouter, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import Optional
import json
from datetime import datetime

from core.utils.supabase_client import get_supabase_client
from core.utils.supabase_service import get_supabase_service_client
from .auth import get_current_user_from_cookie

router = APIRouter(prefix="/admin/media-platforms", tags=["admin-media-platforms"])

# テンプレートは各ルート内で取得
def get_templates():
    from fastapi.templating import Jinja2Templates
    import pathlib
    base_dir = pathlib.Path(__file__).parent.parent
    return Jinja2Templates(directory=str(base_dir / "templates"))

@router.get("/", response_class=HTMLResponse)
async def media_platforms_list(request: Request, user: Optional[dict] = Depends(get_current_user_from_cookie)):
    """媒体プラットフォーム一覧"""
    if not user or user.get("role") != "admin":
        return RedirectResponse(url="/login?error=Unauthorized", status_code=303)
    
    try:
        supabase = get_supabase_client()
        
        # 媒体プラットフォーム一覧を取得（sort_orderで並び替え）
        response = supabase.table("media_platforms").select("*").order("sort_order").execute()
        platforms = response.data if response.data else []
        
        # url_patternsが文字列の場合、リストに変換
        for platform in platforms:
            if platform.get('url_patterns') and isinstance(platform['url_patterns'], str):
                try:
                    platform['url_patterns'] = json.loads(platform['url_patterns'])
                except:
                    platform['url_patterns'] = []
        
        templates = get_templates()
        return templates.TemplateResponse("admin/media_platforms.html", {
            "request": request,
            "current_user": user,
            "platforms": platforms
        })
        
    except Exception as e:
        print(f"Error fetching media platforms: {e}")
        templates = get_templates()
        return templates.TemplateResponse("admin/error.html", {
            "request": request,
            "current_user": user,
            "error": "媒体プラットフォーム一覧の取得に失敗しました"
        })

@router.get("/new", response_class=HTMLResponse)
async def new_media_platform_form(request: Request, user: Optional[dict] = Depends(get_current_user_from_cookie)):
    """新規媒体プラットフォーム作成フォーム"""
    if not user or user.get("role") != "admin":
        return RedirectResponse(url="/login?error=Unauthorized", status_code=303)
    templates = get_templates()
    return templates.TemplateResponse("admin/media_platform_new.html", {
        "request": request,
        "current_user": user
    })

@router.post("/new", response_class=HTMLResponse)
async def create_media_platform(
    request: Request,
    name: str = Form(...),
    display_name: str = Form(...),
    description: Optional[str] = Form(None),
    url_patterns: Optional[str] = Form(None),
    sort_order: int = Form(99),
    is_active: bool = Form(False),
    user: Optional[dict] = Depends(get_current_user_from_cookie)
):
    """媒体プラットフォーム作成"""
    if not user or user.get("role") != "admin":
        return RedirectResponse(url="/login?error=Unauthorized", status_code=303)
    
    try:
        supabase = get_supabase_client()
        
        # URLパターンをJSONとして解析
        url_patterns_list = []
        if url_patterns:
            # カンマ区切りの文字列を配列に変換
            url_patterns_list = [p.strip() for p in url_patterns.split(',') if p.strip()]
        
        # データを構築
        platform_data = {
            "name": name,
            "display_name": display_name,
            "description": description,
            "url_patterns": url_patterns_list,
            "sort_order": sort_order,
            "is_active": is_active,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # 保存
        result = supabase.table("media_platforms").insert(platform_data).execute()
        
        if result.data:
            return RedirectResponse(url="/admin/media-platforms?success=created", status_code=303)
        else:
            return RedirectResponse(url="/admin/media-platforms/new?error=create_failed", status_code=303)
            
    except Exception as e:
        print(f"Error creating media platform: {e}")
        return RedirectResponse(url="/admin/media-platforms/new?error=create_failed", status_code=303)

@router.get("/{platform_id}/edit", response_class=HTMLResponse)
async def edit_media_platform_form(
    request: Request,
    platform_id: str,
    user: Optional[dict] = Depends(get_current_user_from_cookie)
):
    """媒体プラットフォーム編集フォーム"""
    if not user or user.get("role") != "admin":
        return RedirectResponse(url="/login?error=Unauthorized", status_code=303)
    
    try:
        supabase = get_supabase_client()
        
        # 媒体プラットフォーム情報を取得
        response = supabase.table("media_platforms").select("*").eq("id", platform_id).single().execute()
        
        if not response.data:
            return RedirectResponse(url="/admin/media-platforms?error=not_found", status_code=303)
            
        platform = response.data
        
        # URLパターンを文字列に変換
        if platform.get('url_patterns'):
            if isinstance(platform['url_patterns'], list):
                platform['url_patterns_str'] = ', '.join(platform['url_patterns'])
            elif isinstance(platform['url_patterns'], str):
                # 文字列の場合はJSONとしてパース
                try:
                    import json
                    url_patterns_list = json.loads(platform['url_patterns'])
                    platform['url_patterns_str'] = ', '.join(url_patterns_list)
                except:
                    platform['url_patterns_str'] = platform['url_patterns']
            else:
                platform['url_patterns_str'] = ''
        else:
            platform['url_patterns_str'] = ''
            
        templates = get_templates()
        return templates.TemplateResponse("admin/media_platform_edit.html", {
            "request": request,
            "current_user": user,
            "platform": platform
        })
        
    except Exception as e:
        print(f"Error fetching media platform: {e}")
        return RedirectResponse(url="/admin/media-platforms?error=fetch_failed", status_code=303)

@router.post("/{platform_id}/edit", response_class=HTMLResponse)
async def update_media_platform(
    request: Request,
    platform_id: str,
    name: str = Form(...),
    display_name: str = Form(...),
    description: Optional[str] = Form(None),
    url_patterns: Optional[str] = Form(None),
    sort_order: int = Form(99),
    is_active: bool = Form(False),
    user: Optional[dict] = Depends(get_current_user_from_cookie)
):
    """媒体プラットフォーム更新"""
    if not user or user.get("role") != "admin":
        return RedirectResponse(url="/login?error=Unauthorized", status_code=303)
    
    try:
        supabase = get_supabase_client()
        
        # URLパターンをJSONとして解析
        url_patterns_list = []
        if url_patterns:
            # カンマ区切りの文字列を配列に変換
            url_patterns_list = [p.strip() for p in url_patterns.split(',') if p.strip()]
        
        # データを構築
        update_data = {
            "name": name,
            "display_name": display_name,
            "description": description,
            "url_patterns": url_patterns_list,
            "sort_order": sort_order,
            "is_active": is_active,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # 更新
        result = supabase.table("media_platforms").update(update_data).eq("id", platform_id).execute()
        
        if result.data:
            return RedirectResponse(url="/admin/media-platforms?success=updated", status_code=303)
        else:
            return RedirectResponse(url=f"/admin/media-platforms/{platform_id}/edit?error=update_failed", status_code=303)
            
    except Exception as e:
        print(f"Error updating media platform: {e}")
        return RedirectResponse(url=f"/admin/media-platforms/{platform_id}/edit?error=update_failed", status_code=303)

@router.post("/{platform_id}/delete")
async def delete_media_platform(
    platform_id: str,
    user: Optional[dict] = Depends(get_current_user_from_cookie)
):
    """媒体プラットフォーム削除"""
    if not user or user.get("role") != "admin":
        return {"success": False, "error": "Unauthorized"}
    
    try:
        # サービスクライアントを使用（RLSバイパス）
        supabase = get_supabase_service_client()
        
        # まず削除対象が存在するか確認
        check_response = supabase.table("media_platforms").select('id').eq('id', platform_id).execute()
        if not check_response.data:
            return {"success": False, "error": "Media platform not found"}
        
        # 削除実行
        result = supabase.table("media_platforms").delete().eq("id", platform_id).execute()
        
        # 削除結果の確認
        if not result.data:
            raise Exception("削除に失敗しました")
        
        return {"success": True, "message": "Media platform deleted successfully"}
            
    except Exception as e:
        error_msg = str(e)
        if "violates foreign key constraint" in error_msg:
            # 外部キー制約エラー
            print(f"Foreign key constraint error deleting media platform: {error_msg}")
            return {"success": False, "error": "このプラットフォームは他のデータで使用されているため削除できません"}
        else:
            # その他のエラー
            print(f"Error deleting media platform: {error_msg}")
            return {"success": False, "error": "削除に失敗しました"}