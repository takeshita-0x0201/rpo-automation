# Supabase から BigQuery への移行ガイド

## 概要
このドキュメントは、候補者データが大規模化した際の BigQuery 移行手順を説明します。

## 移行判断基準

### 自動監視
`PerformanceMonitor` が以下を監視：
- データ件数が50万件超過
- クエリ応答が2秒超過
- 月間成長率が50%超過

### 手動確認方法
```python
from src.services.performance_monitor import PerformanceMonitor

monitor = PerformanceMonitor()
print(monitor.generate_report())
```

## 移行手順

### Phase 1: 準備
1. BigQueryプロジェクトの作成
2. 認証情報の設定
3. 並行稼働の準備

### Phase 2: データ移行
```python
# 1. Supabaseからデータエクスポート
from supabase import create_client
import pandas as pd

supabase = create_client(url, key)
candidates = supabase.table('candidates').select('*').execute()
df = pd.DataFrame(candidates.data)

# 2. BigQueryへインポート
from google.cloud import bigquery

client = bigquery.Client()
table_id = "rpo-automation.recruitment_data.candidates"

job = client.load_table_from_dataframe(df, table_id)
job.result()
```

### Phase 3: アプリケーション更新
1. 環境変数の追加
   ```bash
   USE_BIGQUERY_FOR_CANDIDATES=true
   GOOGLE_CLOUD_PROJECT=rpo-automation
   ```

2. CandidateCounterの切り替え
   ```python
   class CandidateCounterFactory:
       @staticmethod
       def create():
           if os.getenv('USE_BIGQUERY_FOR_CANDIDATES') == 'true':
               from src.services.candidate_counter_bigquery import BigQueryCandidateCounter
               return BigQueryCandidateCounter()
           else:
               from src.services.candidate_counter import CandidateCounter
               return CandidateCounter()
   ```

### Phase 4: 検証
1. 両システムでカウントを比較
2. パフォーマンステスト
3. 段階的切り替え

## ロールバック手順
1. 環境変数 `USE_BIGQUERY_FOR_CANDIDATES` を `false` に設定
2. アプリケーション再起動
3. Supabaseデータの整合性確認

## コスト比較

### Supabase（現在）
- 無料枠: 500MB まで
- Proプラン: $25/月 + $0.125/GB
- 50万件 ≈ 5GB ≈ $25.625/月

### BigQuery（移行後）
- ストレージ: $0.02/GB/月
- クエリ: $5/TB（最初の1TB無料）
- 50万件 ≈ 5GB ≈ $0.10/月 + クエリ料金

## まとめ
初期はSupabaseのシンプルさを活用し、スケール時にBigQueryへ移行することで、開発効率とコスト効率を両立できます。