"""
Supabaseサービスクライアント
RLSをバイパスする必要がある管理操作用
"""
import os
from supabase import create_client, Client
from typing import Optional

_service_client: Optional[Client] = None

def get_supabase_service_client() -> Client:
    """
    Supabaseサービスクライアントを取得
    SERVICE_KEYを使用してRLSをバイパス
    """
    global _service_client
    
    if _service_client is None:
        url = os.getenv("SUPABASE_URL")
        service_key = os.getenv("SUPABASE_SERVICE_KEY")
        
        if not url or not service_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        
        _service_client = create_client(url, service_key)
    
    return _service_client