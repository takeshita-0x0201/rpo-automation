"""
候補者数カウントサービス
Supabaseから対象候補者数を取得する
"""
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import os
from supabase import create_client, Client

class CandidateCounter:
    def __init__(self):
        self.client = self._get_supabase_client()
        self.table_name = 'candidates'
    
    def _get_supabase_client(self) -> Optional[Client]:
        """Supabaseクライアントを初期化"""
        try:
            url = os.getenv('SUPABASE_URL')
            # SUPABASE_KEYまたはSUPABASE_SERVICE_KEYを使用
            key = os.getenv('SUPABASE_SERVICE_KEY') or os.getenv('SUPABASE_KEY')
            
            if not url or not key:
                raise ValueError("Supabase credentials not found")
            
            return create_client(url, key)
        except Exception as e:
            print(f"Error initializing Supabase client: {e}")
            return None
    
    def count_candidates(self, job_parameters: Dict[str, Any], client_id: Optional[str] = None, requirement_id: Optional[str] = None) -> Optional[int]:
        """
        ジョブパラメータに基づいて対象候補者数をカウント
        
        Args:
            job_parameters: ジョブのパラメータ
                - data_source: "latest" または "date_range"
                - start_date: 開始日（date_range時）
                - end_date: 終了日（date_range時）
            client_id: クライアントID（オプション）
            requirement_id: 採用要件ID（オプション）
        
        Returns:
            候補者数、エラー時はNone
        """
        if not self.client:
            return None
        
        try:
            # ベースクエリ
            query = self.client.table(self.table_name).select('id', count='exact')
            
            data_source = job_parameters.get('data_source', 'latest')
            
            if data_source == 'latest':
                # 最新30日間のデータ
                thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()
                query = query.gte('scraped_at', thirty_days_ago)
            
            elif data_source == 'date_range':
                # 指定期間のデータ
                start_date = job_parameters.get('start_date')
                end_date = job_parameters.get('end_date')
                
                if not start_date or not end_date:
                    return None
                
                # 日付をISO形式に変換
                start_datetime = f"{start_date}T00:00:00"
                end_datetime = f"{end_date}T23:59:59"
                
                query = query.gte('scraped_at', start_datetime).lte('scraped_at', end_datetime)
            
            else:
                return None
            
            # クライアントIDでフィルタ（新しいテーブル構造では直接カラム）
            if client_id:
                query = query.eq('client_id', client_id)
            
            # 採用要件IDでフィルタ
            if requirement_id:
                query = query.eq('requirement_id', requirement_id)
            
            # カウントを取得
            result = query.execute()
            
            # Supabaseのcount機能を使用
            return result.count if hasattr(result, 'count') else len(result.data)
            
        except Exception as e:
            print(f"Error counting candidates: {e}")
            return None
    
    def count_by_requirement(self, requirement_id: str) -> Optional[int]:
        """
        特定の採用要件IDに対する候補者数をカウント
        
        Args:
            requirement_id: 採用要件ID
        
        Returns:
            候補者数、エラー時はNone
        """
        if not self.client or not requirement_id:
            return None
        
        try:
            # 要件IDでフィルタしてカウント
            result = self.client.table(self.table_name)\
                .select('id', count='exact')\
                .eq('requirement_id', requirement_id)\
                .execute()
            
            return result.count if hasattr(result, 'count') else len(result.data)
            
        except Exception as e:
            print(f"Error counting candidates by requirement: {e}")
            return None
    
    def count_by_client(self, client_id: str) -> Optional[int]:
        """
        特定のクライアントIDに対する候補者数をカウント
        
        Args:
            client_id: クライアントID
        
        Returns:
            候補者数、エラー時はNone
        """
        if not self.client or not client_id:
            return None
        
        try:
            # クライアントIDでフィルタしてカウント
            result = self.client.table(self.table_name)\
                .select('id', count='exact')\
                .eq('client_id', client_id)\
                .execute()
            
            return result.count if hasattr(result, 'count') else len(result.data)
            
        except Exception as e:
            print(f"Error counting candidates by client: {e}")
            return None
    
    def get_error_message(self) -> str:
        """
        エラー時のメッセージを返す
        
        Returns:
            エラーメッセージ
        """
        return "取得エラー"