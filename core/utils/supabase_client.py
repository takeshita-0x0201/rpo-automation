"""
Supabaseクライアントの初期化と共通処理
"""
import os
from supabase import create_client, Client
from dotenv import load_dotenv
from typing import Optional, Dict, Any

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
    print(f"Getting role for user_id: {user_id}")
    try:
        result = supabase.table('profiles')\
            .select('role')\
            .eq('id', user_id)\
            .execute()
        
        print(f"Profile query result: {result}")
        
        if result.data and len(result.data) > 0:
            role = result.data[0]['role']
            print(f"Found role: {role}")
            return role
        else:
            print("No profile found for user")
            return None
    except Exception as e:
        print(f"Error getting user role: {e}")
        return None

def is_admin_or_manager(supabase: Client, user_id: str) -> bool:
    """ユーザーが管理者またはマネージャーか確認"""
    role = get_user_role(supabase, user_id)
    return role in ['admin', 'manager']

class SupabaseAuth:
    """Supabase認証のヘルパークラス"""
    
    @staticmethod
    async def sign_in(email: str, password: str) -> Dict[str, Any]:
        """メールアドレスとパスワードでサインイン"""
        try:
            supabase = get_supabase_client()
            response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            print(f"Auth response: {response}")
            
            # ユーザーのロールを取得
            user_role = get_user_role(supabase, response.user.id) if response.user else None
            print(f"User role from DB: {user_role}")
            
            # ロールがない場合はデフォルトで'user'を設定
            if not user_role:
                user_role = 'user'
                print(f"No role found, defaulting to: {user_role}")
            
            return {
                "success": True,
                "user": response.user,
                "session": response.session,
                "role": user_role
            }
        except Exception as e:
            print(f"Sign in error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    async def sign_out() -> bool:
        """サインアウト"""
        try:
            supabase = get_supabase_client()
            supabase.auth.sign_out()
            return True
        except Exception:
            return False
    
    @staticmethod
    async def get_current_user(access_token: str) -> Optional[Dict[str, Any]]:
        """現在のユーザー情報を取得"""
        try:
            supabase = get_supabase_client()
            user = supabase.auth.get_user(access_token)
            if user and user.user:
                role = get_user_role(supabase, user.user.id)
                return {
                    "user": user.user,
                    "role": role
                }
            return None
        except Exception:
            return None