"""
データベースパフォーマンス監視サービス
将来的なBigQuery移行の判断材料として使用
"""
import time
from datetime import datetime
from typing import Dict, Any, Optional
import os
from supabase import create_client, Client

class PerformanceMonitor:
    def __init__(self):
        self.client = self._get_supabase_client()
        self.slow_query_threshold = 1.0  # 1秒以上を遅いクエリとする
        self.migration_threshold = {
            'row_count': 500000,  # 50万件
            'query_time': 2.0,  # 2秒
            'monthly_growth_rate': 0.5  # 月50%成長
        }
    
    def _get_supabase_client(self) -> Optional[Client]:
        """Supabaseクライアントを初期化"""
        try:
            url = os.getenv('SUPABASE_URL')
            key = os.getenv('SUPABASE_KEY')
            
            if not url or not key:
                return None
            
            return create_client(url, key)
        except:
            return None
    
    def check_query_performance(self, table_name: str = 'candidates') -> Dict[str, Any]:
        """
        テーブルのクエリパフォーマンスをチェック
        
        Returns:
            パフォーマンス情報
        """
        if not self.client:
            return {'error': 'Client not initialized'}
        
        results = {}
        
        # 1. 総件数カウント
        start_time = time.time()
        try:
            count_result = self.client.table(table_name).select('id', count='exact').execute()
            count_duration = time.time() - start_time
            total_count = count_result.count if hasattr(count_result, 'count') else 0
            
            results['total_count'] = total_count
            results['count_query_time'] = count_duration
            results['count_query_slow'] = count_duration > self.slow_query_threshold
        except Exception as e:
            results['count_error'] = str(e)
        
        # 2. 最新30日間のデータ取得
        start_time = time.time()
        try:
            recent_result = self.client.table(table_name)\
                .select('id', count='exact')\
                .gte('scraped_at', datetime.now().isoformat())\
                .execute()
            recent_duration = time.time() - start_time
            recent_count = recent_result.count if hasattr(recent_result, 'count') else 0
            
            results['recent_count'] = recent_count
            results['recent_query_time'] = recent_duration
            results['recent_query_slow'] = recent_duration > self.slow_query_threshold
        except Exception as e:
            results['recent_error'] = str(e)
        
        # 3. 複雑なクエリ（会社別集計）
        start_time = time.time()
        try:
            # Supabaseでは集計が限定的なので、データ取得して計算
            company_result = self.client.table(table_name)\
                .select('current_company')\
                .limit(10000)\
                .execute()
            company_duration = time.time() - start_time
            
            results['complex_query_time'] = company_duration
            results['complex_query_slow'] = company_duration > self.slow_query_threshold
        except Exception as e:
            results['complex_error'] = str(e)
        
        # 4. 移行推奨の判定
        results['migration_recommended'] = self._check_migration_criteria(results)
        
        return results
    
    def _check_migration_criteria(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        BigQuery移行の推奨基準をチェック
        
        Returns:
            移行推奨情報
        """
        criteria = {
            'should_migrate': False,
            'reasons': []
        }
        
        # 件数基準
        if metrics.get('total_count', 0) > self.migration_threshold['row_count']:
            criteria['should_migrate'] = True
            criteria['reasons'].append(f"データ件数が{self.migration_threshold['row_count']:,}件を超過")
        
        # パフォーマンス基準
        slow_queries = [
            ('カウントクエリ', metrics.get('count_query_time', 0)),
            ('最新データクエリ', metrics.get('recent_query_time', 0)),
            ('複雑クエリ', metrics.get('complex_query_time', 0))
        ]
        
        for query_name, duration in slow_queries:
            if duration > self.migration_threshold['query_time']:
                criteria['should_migrate'] = True
                criteria['reasons'].append(f"{query_name}が{duration:.2f}秒（基準: {self.migration_threshold['query_time']}秒）")
        
        return criteria
    
    def get_growth_rate(self, table_name: str = 'candidates', days: int = 30) -> Optional[float]:
        """
        指定期間のデータ成長率を計算
        
        Returns:
            月間成長率（%）
        """
        if not self.client:
            return None
        
        try:
            # 30日前のデータ件数
            thirty_days_ago = datetime.now().isoformat()
            old_count = self.client.table(table_name)\
                .select('id', count='exact')\
                .lt('scraped_at', thirty_days_ago)\
                .execute()
            
            # 現在の総件数
            current_count = self.client.table(table_name)\
                .select('id', count='exact')\
                .execute()
            
            old_total = old_count.count if hasattr(old_count, 'count') else 0
            current_total = current_count.count if hasattr(current_count, 'count') else 0
            
            if old_total == 0:
                return None
            
            growth_rate = ((current_total - old_total) / old_total) * 100
            return growth_rate
            
        except:
            return None
    
    def generate_report(self) -> str:
        """
        パフォーマンスレポートを生成
        
        Returns:
            レポート文字列
        """
        metrics = self.check_query_performance()
        growth_rate = self.get_growth_rate()
        
        report = "=== データベースパフォーマンスレポート ===\n\n"
        report += f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        report += "【データ統計】\n"
        report += f"- 総件数: {metrics.get('total_count', 'N/A'):,}件\n"
        report += f"- 最新30日間: {metrics.get('recent_count', 'N/A'):,}件\n"
        if growth_rate is not None:
            report += f"- 月間成長率: {growth_rate:.1f}%\n"
        report += "\n"
        
        report += "【クエリパフォーマンス】\n"
        report += f"- カウントクエリ: {metrics.get('count_query_time', 'N/A'):.3f}秒 "
        if metrics.get('count_query_slow'):
            report += "⚠️ 遅延"
        report += "\n"
        
        report += f"- 最新データクエリ: {metrics.get('recent_query_time', 'N/A'):.3f}秒 "
        if metrics.get('recent_query_slow'):
            report += "⚠️ 遅延"
        report += "\n"
        
        report += f"- 複雑クエリ: {metrics.get('complex_query_time', 'N/A'):.3f}秒 "
        if metrics.get('complex_query_slow'):
            report += "⚠️ 遅延"
        report += "\n\n"
        
        migration_info = metrics.get('migration_recommended', {})
        if migration_info.get('should_migrate'):
            report += "【⚠️ BigQuery移行推奨】\n"
            for reason in migration_info.get('reasons', []):
                report += f"- {reason}\n"
        else:
            report += "【✅ パフォーマンス良好】\n"
            report += "- 現時点でBigQuery移行は不要です\n"
        
        return report