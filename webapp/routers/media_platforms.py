from fastapi import APIRouter, Depends, HTTPException
from typing import List
from core.utils.supabase_client import get_supabase_client

router = APIRouter()

@router.get("/media_platforms")
async def get_media_platforms():
    """
    アクティブな媒体プラットフォーム一覧を取得
    """
    try:
        supabase = get_supabase_client()
        # is_activeがTrueのレコードのみ取得し、sort_orderで並び替え
        response = supabase.table("media_platforms").select("*").eq("is_active", True).order("sort_order").execute()
        
        if response.data:
            # url_patternsを文字列からリストに変換
            import json
            for platform in response.data:
                if platform.get('url_patterns') and isinstance(platform['url_patterns'], str):
                    try:
                        platform['url_patterns'] = json.loads(platform['url_patterns'])
                    except:
                        platform['url_patterns'] = []
            
            return {
                "success": True,
                "platforms": response.data
            }
        else:
            return {
                "success": True,
                "platforms": []
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch media platforms: {str(e)}")

@router.get("/media_platforms/{platform_id}")
async def get_media_platform(
    platform_id: str
):
    """
    特定の媒体プラットフォーム情報を取得
    """
    try:
        supabase = get_supabase_client()
        response = supabase.table("media_platforms").select("*").eq("id", platform_id).single().execute()
        
        if response.data:
            return {
                "success": True,
                "platform": response.data
            }
        else:
            raise HTTPException(status_code=404, detail="Media platform not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch media platform: {str(e)}")