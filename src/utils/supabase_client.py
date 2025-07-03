"""
Supabaseクライアントの初期化と共通処理
"""
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

def get_supabase_client() -> Client:
    """Supabaseクライアントを取得"""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    
    if not url or not key:
        raise ValueError("Supabase credentials not found in environment variables")
    
    return create_client(url, key)

def get_authenticated_user(supabase: Client, access_token: str):
    """アクセストークンからユーザー情報を取得"""
    try:
        user = supabase.auth.get_user(access_token)
        return user
    except Exception as e:
        print(f"Authentication error: {e}")
        return None

def get_user_role(supabase: Client, user_id: str) -> str:
    """ユーザーの役職を取得"""
    result = supabase.table('profiles')\
        .select('role')\
        .eq('id', user_id)\
        .execute()
    
    if result.data and len(result.data) > 0:
        return result.data[0]['role']
    return None

def is_admin_or_manager(supabase: Client, user_id: str) -> bool:
    """ユーザーが管理者またはマネージャーか確認"""
    role = get_user_role(supabase, user_id)
    return role in ['admin', 'manager']