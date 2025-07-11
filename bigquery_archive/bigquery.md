# BigQueryセットアップガイド

このガイドでは、RPO自動化システムで使用するBigQueryプロジェクトの詳細なセットアップ手順を説明します。

## 目次

- [BigQuery APIの有効化](#bigquery-apiの有効化)
- [データセットの作成](#データセットの作成)
- [テーブルの作成](#テーブルの作成)
- [サービスアカウントの設定](#サービスアカウントの設定)
- [接続テスト](#接続テスト)
- [パーティショニングとクラスタリング](#パーティショニングとクラスタリング)
- [ストアドプロシージャの作成](#ストアドプロシージャの作成)
- [コスト管理](#コスト管理)
- [監視とアラート](#監視とアラート)

---

## BigQuery APIの有効化

### 1. Google Cloud Consoleでの設定

```bash
# gcloud CLIで一括有効化
gcloud services enable \
    bigquery.googleapis.com \
    bigquerydatatransfer.googleapis.com \
    cloudresourcemanager.googleapis.com \
    logging.googleapis.com \
    monitoring.googleapis.com
```

### 2. 有効化の確認

```bash
# 有効化されたAPIの確認
gcloud services list --enabled --filter="name:bigquery"
```

---

## データセットの作成

### 1. データセット構成の設計

本システムでは以下のデータセット構成を使用します：

```
your-project/
├── rpo_raw_data/          # スクレイピング生データ
├── rpo_structured_data/   # AI構造化済みデータ  
├── rpo_matching_results/  # AI判定結果
└── system_logs/           # システムログ・エラー情報
```

### 2. gcloudコマンドでの作成

```bash
# プロジェクトIDを設定
export PROJECT_ID="your-project-id"
export LOCATION="asia-northeast1"  # 東京リージョン

# 各データセットを作成
bq mk --location=$LOCATION --dataset $PROJECT_ID:rpo_raw_data
bq mk --location=$LOCATION --dataset $PROJECT_ID:rpo_structured_data  
bq mk --location=$LOCATION --dataset $PROJECT_ID:rpo_matching_results
bq mk --location=$LOCATION --dataset $PROJECT_ID:system_logs

# データセット一覧の確認
bq ls --max_results=10
```

### 3. Google Cloud Consoleでの作成

1. [BigQuery Console](https://console.cloud.google.com/bigquery)を開く
2. プロジェクト名の右側の「︙」→「データセットを作成」
3. 各データセットを以下の設定で作成：

```
データセットID: rpo_raw_data
データのロケーション: asia-northeast1 (Tokyo)
デフォルトのテーブル有効期限: なし
暗号化: Google管理の暗号化キー
```

---

## テーブルの作成

### 1. raw_data データセットのテーブル

#### raw_candidates（候補者生データ）

```sql
CREATE TABLE `{project_id}.rpo_raw_data.raw_candidates` (
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    session_id STRING NOT NULL,
    client_id STRING NOT NULL,
    client_name STRING,
    candidate_url STRING NOT NULL,
    raw_html STRING,
    raw_data JSON,
    scraped_by_user_id STRING,
    ingestion_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY DATE(scraped_at)
CLUSTER BY client_id, session_id
OPTIONS (
    description = "Bizreachからスクレイピングした候補者の生データ",
    partition_expiration_days = 90
);
```

#### raw_scraping_sessions（スクレイピングセッション）

```sql
CREATE TABLE `{project_id}.rpo_raw_data.raw_scraping_sessions` (
    session_id STRING NOT NULL,
    user_id STRING NOT NULL,
    client_id STRING NOT NULL,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    total_candidates_found INTEGER DEFAULT 0,
    status STRING DEFAULT 'running',
    error_message STRING,
    session_metadata JSON
)
PARTITION BY DATE(started_at)
CLUSTER BY user_id, client_id;
```

### 2. structured_data データセットのテーブル

#### structured_candidates（構造化済み候補者データ）

```sql
CREATE TABLE `{project_id}.rpo_structured_data.structured_candidates` (
    candidate_id STRING NOT NULL,
    original_url STRING NOT NULL,
    client_id STRING NOT NULL,
    name STRING,
    email STRING,
    phone STRING,
    current_company STRING,
    current_position STRING,
    skills ARRAY<STRING>,
    experience_years INTEGER,
    education STRING,
    location STRING,
    salary_expectation STRUCT<
        min INTEGER,
        max INTEGER,
        currency STRING
    >,
    structured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    structured_data JSON,
    structuring_model STRING DEFAULT 'gemini-pro',
    confidence_score FLOAT64
)
PARTITION BY DATE(structured_at)
CLUSTER BY client_id, current_company
OPTIONS (
    description = "AIによって構造化された候補者データ"
);
```

#### job_requirements（採用要件スナップショット）

```sql
CREATE TABLE `{project_id}.rpo_structured_data.job_requirements` (
    id STRING NOT NULL,
    client_id STRING NOT NULL,
    title STRING NOT NULL,
    position STRING,
    description STRING,
    required_skills ARRAY<STRING>,
    preferred_skills ARRAY<STRING>,
    experience_years INTEGER,
    education_level STRING,
    salary_range STRUCT<
        min INTEGER,
        max INTEGER,
        currency STRING
    >,
    work_location STRING,
    employment_type STRING,
    original_text STRING,
    structured_data JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    created_by STRING
)
PARTITION BY DATE(created_at)
CLUSTER BY client_id;
```

### 3. matching_results データセットのテーブル

#### matching_results（マッチング結果）

```sql
CREATE TABLE `{project_id}.rpo_matching_results.matching_results` (
    result_id STRING NOT NULL,
    job_id STRING NOT NULL,
    candidate_id STRING NOT NULL,
    client_id STRING NOT NULL,
    requirement_id STRING NOT NULL,
    match_score FLOAT64,
    match_reasons ARRAY<STRING>,
    concerns ARRAY<STRING>,
    ai_evaluation JSON,
    evaluated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    evaluation_model STRING DEFAULT 'gpt-4',
    model_version STRING,
    processing_time_seconds FLOAT64
)
PARTITION BY DATE(evaluated_at)
CLUSTER BY client_id, job_id, match_score DESC
OPTIONS (
    description = "AIによる候補者マッチング結果"
);
```

#### evaluation_summaries（評価サマリー）

```sql
CREATE TABLE `{project_id}.rpo_matching_results.evaluation_summaries` (
    job_id STRING NOT NULL,
    client_id STRING NOT NULL,
    requirement_id STRING NOT NULL,
    total_candidates INTEGER,
    high_match_count INTEGER,    -- スコア80以上
    medium_match_count INTEGER,  -- スコア60-79
    low_match_count INTEGER,     -- スコア60未満
    avg_match_score FLOAT64,
    evaluation_completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    summary_data JSON
)
PARTITION BY DATE(evaluation_completed_at)
CLUSTER BY client_id;
```

### 4. system_logs データセットのテーブル

#### application_logs（アプリケーションログ）

```sql
CREATE TABLE `{project_id}.system_logs.application_logs` (
    log_id STRING NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    level STRING,  -- INFO, WARNING, ERROR, CRITICAL
    source STRING, -- web_app, chrome_extension, cloud_function
    message STRING,
    user_id STRING,
    session_id STRING,
    error_details JSON,
    stack_trace STRING
)
PARTITION BY DATE(timestamp)
CLUSTER BY level, source
OPTIONS (
    partition_expiration_days = 30
);
```

#### api_access_logs（API アクセスログ）

```sql
CREATE TABLE `{project_id}.system_logs.api_access_logs` (
    request_id STRING NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    method STRING,
    endpoint STRING,
    user_id STRING,
    ip_address STRING,
    user_agent STRING,
    response_status INTEGER,
    response_time_ms INTEGER,
    request_size_bytes INTEGER,
    response_size_bytes INTEGER
)
PARTITION BY DATE(timestamp)
CLUSTER BY endpoint, response_status;
```

### 5. 一括テーブル作成スクリプト

```bash
#!/bin/bash
# create_bigquery_tables.sh

PROJECT_ID="your-project-id"

# SQLファイルのディレクトリ
SQL_DIR="./sql/bigquery"

# 各SQLファイルを実行
for sql_file in $SQL_DIR/*.sql; do
    echo "Executing $sql_file..."
    
    # プロジェクトIDを置換してクエリ実行
    sed "s/{project_id}/$PROJECT_ID/g" "$sql_file" | bq query --use_legacy_sql=false
    
    if [ $? -eq 0 ]; then
        echo "✅ Successfully executed $sql_file"
    else
        echo "❌ Failed to execute $sql_file"
        exit 1
    fi
done

echo "🎉 All tables created successfully!"
```

---

## サービスアカウントの設定

### 1. サービスアカウントの作成

```bash
# BigQuery専用サービスアカウントを作成
gcloud iam service-accounts create rpo-automation-bigquery \
    --display-name="RPO Automation BigQuery Service Account" \
    --description="Service account for RPO automation system BigQuery access"
```

### 2. 権限の付与

```bash
PROJECT_ID="your-project-id"
SERVICE_ACCOUNT="rpo-automation-bigquery@${PROJECT_ID}.iam.gserviceaccount.com"

# BigQuery Data Editor（データの読み書き）
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/bigquery.dataEditor"

# BigQuery Job User（クエリ実行）
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/bigquery.jobUser"

# Logging Writer（ログ出力）
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/logging.logWriter"
```

### 3. キーファイルの作成

```bash
# 認証キーをダウンロード
gcloud iam service-accounts keys create ./credentials/bigquery-service-account.json \
    --iam-account=$SERVICE_ACCOUNT

# 権限の確認
chmod 600 ./credentials/bigquery-service-account.json
```

### 4. 最小権限の原則によるカスタムロール

```bash
# カスタムロールを作成（推奨）
gcloud iam roles create rpo.bigquery.limited \
    --project=$PROJECT_ID \
    --title="RPO BigQuery Limited Access" \
    --description="Limited BigQuery access for RPO automation" \
    --permissions=bigquery.datasets.get,bigquery.tables.get,bigquery.tables.list,bigquery.tables.create,bigquery.tables.update,bigquery.tables.getData,bigquery.tables.updateData,bigquery.jobs.create

# カスタムロールを適用
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="projects/$PROJECT_ID/roles/rpo.bigquery.limited"
```

---

## 接続テスト

### 1. Python クライアントでの接続テスト

```python
# test_bigquery_connection.py
import os
from google.cloud import bigquery
from google.oauth2 import service_account
from dotenv import load_dotenv

def test_bigquery_connection():
    load_dotenv()
    
    # 認証情報の設定
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    project_id = os.getenv("BIGQUERY_PROJECT_ID")
    
    print(f"Project ID: {project_id}")
    print(f"Credentials: {credentials_path}")
    
    try:
        # クライアントの初期化
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path
        )
        client = bigquery.Client(
            credentials=credentials,
            project=project_id
        )
        
        # データセット一覧の取得
        datasets = list(client.list_datasets())
        print(f"✅ Connection successful!")
        print(f"Found {len(datasets)} datasets:")
        
        for dataset in datasets:
            print(f"  - {dataset.dataset_id}")
            
            # 各データセットのテーブル一覧
            dataset_ref = client.dataset(dataset.dataset_id)
            tables = list(client.list_tables(dataset_ref))
            print(f"    Tables: {len(tables)}")
            
            for table in tables[:3]:  # 最初の3つのテーブルのみ表示
                print(f"      - {table.table_id}")
        
        # テストクエリの実行
        test_query = """
        SELECT 
            table_name,
            table_type,
            creation_time
        FROM `{}.rpo_raw_data.INFORMATION_SCHEMA.TABLES`
        LIMIT 5
        """.format(project_id)
        
        query_job = client.query(test_query)
        results = query_job.result()
        
        print("\n✅ Test query successful!")
        print("Tables in rpo_raw_data:")
        for row in results:
            print(f"  - {row.table_name} ({row.table_type})")
            
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        import traceback
        traceback.print_exc()

def test_data_insertion():
    """データ挿入テスト"""
    load_dotenv()
    
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    project_id = os.getenv("BIGQUERY_PROJECT_ID")
    
    credentials = service_account.Credentials.from_service_account_file(
        credentials_path
    )
    client = bigquery.Client(credentials=credentials, project=project_id)
    
    # テストデータの挿入
    table_id = f"{project_id}.system_logs.application_logs"
    
    rows_to_insert = [
        {
            "log_id": "test-001",
            "level": "INFO",
            "source": "test_script",
            "message": "BigQuery connection test successful",
            "user_id": "test-user"
        }
    ]
    
    try:
        errors = client.insert_rows_json(table_id, rows_to_insert)
        if errors:
            print(f"❌ Insert errors: {errors}")
        else:
            print("✅ Test data inserted successfully!")
            
    except Exception as e:
        print(f"❌ Insert failed: {e}")

if __name__ == "__main__":
    test_bigquery_connection()
    test_data_insertion()
```

### 2. 実行方法

```bash
# 環境変数を設定
export GOOGLE_APPLICATION_CREDENTIALS="./credentials/bigquery-service-account.json"
export BIGQUERY_PROJECT_ID="your-project-id"

# テスト実行
python test_bigquery_connection.py
```

---

## パーティショニングとクラスタリング

### 1. パーティショニング戦略

各テーブルの時系列データに対してパーティショニングを適用：

```sql
-- 日付パーティショニング（推奨）
PARTITION BY DATE(scraped_at)

-- 月単位パーティショニング（大量データの場合）
PARTITION BY DATE_TRUNC(scraped_at, MONTH)

-- 範囲パーティショニング（数値カラム）
PARTITION BY RANGE_BUCKET(match_score, GENERATE_ARRAY(0, 100, 10))
```

### 2. クラスタリング戦略

頻繁に使用される検索条件でクラスタリングを設定：

```sql
-- 候補者データ: client_id → session_id
CLUSTER BY client_id, session_id

-- マッチング結果: client_id → job_id → match_score (降順)
CLUSTER BY client_id, job_id, match_score DESC

-- ログデータ: level → source
CLUSTER BY level, source
```

### 3. パーティション管理の自動化

```sql
-- パーティション有効期限の設定
ALTER TABLE `{project_id}.rpo_raw_data.raw_candidates` 
SET OPTIONS (partition_expiration_days = 90);

-- 古いパーティションの手動削除
DROP TABLE `{project_id}.rpo_raw_data.raw_candidates$20231201`;
```

---

## ストアドプロシージャの作成

### 1. データ品質チェック用プロシージャ

```sql
-- データ品質チェック
CREATE OR REPLACE PROCEDURE `{project_id}.system_logs.check_data_quality`()
BEGIN
    DECLARE candidate_duplicates INT64;
    DECLARE missing_urls INT64;
    
    -- 重複候補者のチェック
    SELECT COUNT(*) INTO candidate_duplicates
    FROM (
        SELECT candidate_url, COUNT(*) as cnt
        FROM `{project_id}.rpo_structured_data.structured_candidates`
        GROUP BY candidate_url
        HAVING cnt > 1
    );
    
    -- 必須フィールドの欠損チェック
    SELECT COUNT(*) INTO missing_urls
    FROM `{project_id}.rpo_structured_data.structured_candidates`
    WHERE candidate_url IS NULL OR candidate_url = '';
    
    -- ログに結果を記録
    INSERT INTO `{project_id}.system_logs.application_logs`
    (log_id, level, source, message)
    VALUES
    (GENERATE_UUID(), 'INFO', 'data_quality_check', 
     FORMAT('Quality check completed. Duplicates: %d, Missing URLs: %d', 
            candidate_duplicates, missing_urls));
    
    -- 結果を返す
    SELECT 
        candidate_duplicates as duplicate_candidates,
        missing_urls as missing_required_fields,
        CURRENT_TIMESTAMP() as checked_at;
END;
```

### 2. 古いデータのアーカイブ用プロシージャ

```sql
-- 古いログデータのアーカイブ
CREATE OR REPLACE PROCEDURE `{project_id}.system_logs.archive_old_logs`(
    retention_days INT64 DEFAULT 30
)
BEGIN
    DECLARE deleted_count INT64;
    
    -- 30日以上古いログを削除
    DELETE FROM `{project_id}.system_logs.application_logs`
    WHERE DATE(timestamp) < DATE_SUB(CURRENT_DATE(), INTERVAL retention_days DAY);
    
    SET deleted_count = @@row_count;
    
    -- アーカイブ完了ログ
    INSERT INTO `{project_id}.system_logs.application_logs`
    (log_id, level, source, message)
    VALUES
    (GENERATE_UUID(), 'INFO', 'archive_procedure', 
     FORMAT('Archived %d old log entries (older than %d days)', 
            deleted_count, retention_days));
END;
```

### 3. 統計情報更新用プロシージャ

```sql
-- マッチング統計の更新
CREATE OR REPLACE PROCEDURE `{project_id}.rpo_matching_results.update_evaluation_summaries`(
    job_id STRING
)
BEGIN
    -- 既存サマリーを削除
    DELETE FROM `{project_id}.rpo_matching_results.evaluation_summaries`
    WHERE job_id = job_id;
    
    -- 新しいサマリーを計算・挿入
    INSERT INTO `{project_id}.rpo_matching_results.evaluation_summaries`
    (job_id, client_id, requirement_id, total_candidates, 
     high_match_count, medium_match_count, low_match_count, avg_match_score)
    SELECT 
        job_id,
        client_id,
        requirement_id,
        COUNT(*) as total_candidates,
        SUM(CASE WHEN match_score >= 80 THEN 1 ELSE 0 END) as high_match_count,
        SUM(CASE WHEN match_score >= 60 AND match_score < 80 THEN 1 ELSE 0 END) as medium_match_count,
        SUM(CASE WHEN match_score < 60 THEN 1 ELSE 0 END) as low_match_count,
        AVG(match_score) as avg_match_score
    FROM `{project_id}.rpo_matching_results.matching_results`
    WHERE job_id = job_id
    GROUP BY job_id, client_id, requirement_id;
END;
```

---

## コスト管理

### 1. クエリコストの監視

```sql
-- 高コストクエリの確認
SELECT
    job_id,
    user_email,
    query,
    total_bytes_processed,
    total_bytes_billed,
    total_slot_ms,
    creation_time
FROM `region-asia-northeast1`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
    AND total_bytes_billed > 1000000000  -- 1GB以上
ORDER BY total_bytes_billed DESC
LIMIT 10;
```

### 2. 月間使用量の確認

```sql
-- 月間クエリ使用量
SELECT
    DATE_TRUNC(creation_time, MONTH) as month,
    SUM(total_bytes_processed) / (1024*1024*1024) as total_gb_processed,
    SUM(total_bytes_billed) / (1024*1024*1024) as total_gb_billed,
    COUNT(*) as query_count
FROM `region-asia-northeast1`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 6 MONTH)
    AND job_type = 'QUERY'
GROUP BY month
ORDER BY month DESC;
```

### 3. コスト最適化のベストプラクティス

```sql
-- ❌ 悪い例: 全カラム取得
SELECT *
FROM `{project_id}.rpo_structured_data.structured_candidates`
WHERE DATE(structured_at) = CURRENT_DATE();

-- ✅ 良い例: 必要なカラムのみ
SELECT candidate_id, name, current_company, skills
FROM `{project_id}.rpo_structured_data.structured_candidates`
WHERE DATE(structured_at) = CURRENT_DATE();

-- ✅ パーティション活用
SELECT candidate_id, name, current_company
FROM `{project_id}.rpo_structured_data.structured_candidates`
WHERE structured_at >= TIMESTAMP('2023-12-01')
    AND structured_at < TIMESTAMP('2023-12-02');
```

### 4. クエリ実行前のコスト見積もり

```python
def estimate_query_cost(client, query):
    """クエリの実行コストを見積もり"""
    job_config = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
    
    job = client.query(query, job_config=job_config)
    
    bytes_processed = job.total_bytes_processed
    gb_processed = bytes_processed / (1024**3)
    estimated_cost_usd = gb_processed * 0.005  # $5 per TB
    
    print(f"Estimated bytes processed: {bytes_processed:,}")
    print(f"Estimated GB processed: {gb_processed:.2f}")
    print(f"Estimated cost: ${estimated_cost_usd:.4f}")
    
    return gb_processed
```

---

## 監視とアラート

### 1. Cloud Monitoringでの監視設定

```bash
# カスタムメトリクスの作成
gcloud logging metrics create bigquery_error_rate \
    --description="BigQuery error rate" \
    --log-filter='resource.type="bigquery_resource" AND severity="ERROR"'
```

### 2. アラートポリシーの設定

```yaml
# alert-policy.yaml
displayName: "BigQuery High Error Rate"
conditions:
  - displayName: "Error rate exceeds threshold"
    conditionThreshold:
      filter: 'metric.type="logging.googleapis.com/user/bigquery_error_rate"'
      comparison: COMPARISON_GREATER_THAN
      thresholdValue: 5
      duration: 300s
notificationChannels:
  - "projects/your-project/notificationChannels/your-channel-id"
```

### 3. データ品質監視

```sql
-- 毎日の自動データ品質チェック
CREATE OR REPLACE TABLE FUNCTION `{project_id}.system_logs.daily_quality_check`()
RETURNS TABLE<metric_name STRING, metric_value INT64, check_date DATE>
AS (
    SELECT 'total_candidates' as metric_name, 
           COUNT(*) as metric_value,
           CURRENT_DATE() as check_date
    FROM `{project_id}.rpo_structured_data.structured_candidates`
    WHERE DATE(structured_at) = CURRENT_DATE()
    
    UNION ALL
    
    SELECT 'missing_skills' as metric_name,
           COUNT(*) as metric_value, 
           CURRENT_DATE() as check_date
    FROM `{project_id}.rpo_structured_data.structured_candidates`
    WHERE DATE(structured_at) = CURRENT_DATE()
        AND (skills IS NULL OR ARRAY_LENGTH(skills) = 0)
        
    UNION ALL
    
    SELECT 'duplicate_candidates' as metric_name,
           COUNT(*) - COUNT(DISTINCT candidate_url) as metric_value,
           CURRENT_DATE() as check_date
    FROM `{project_id}.rpo_structured_data.structured_candidates`
    WHERE DATE(structured_at) = CURRENT_DATE()
);
```

---

## データ保持とアーカイブ

### 1. 自動データ削除の設定

```sql
-- テーブルレベルでのTTL設定
ALTER TABLE `{project_id}.system_logs.application_logs`
SET OPTIONS (
    partition_expiration_days = 30,
    description = "Application logs with 30-day retention"
);

-- パーティションレベルでの期限設定
ALTER TABLE `{project_id}.rpo_raw_data.raw_candidates`
SET OPTIONS (partition_expiration_days = 90);
```

### 2. アーカイブ戦略

```bash
#!/bin/bash
# archive_old_data.sh

PROJECT_ID="your-project-id"
ARCHIVE_BUCKET="gs://your-archive-bucket"
DATE_THRESHOLD="2023-01-01"

# 古いデータをCloud Storageにエクスポート
bq extract \
    --destination_format=AVRO \
    --compression=SNAPPY \
    "${PROJECT_ID}:rpo_raw_data.raw_candidates\$${DATE_THRESHOLD//-/}" \
    "${ARCHIVE_BUCKET}/candidates/year=2023/candidates_*.avro"

# エクスポート成功後、BigQueryから削除
if [ $? -eq 0 ]; then
    bq rm -f -t "${PROJECT_ID}:rpo_raw_data.raw_candidates\$${DATE_THRESHOLD//-/}"
    echo "Archived and removed partition for $DATE_THRESHOLD"
fi
```

---

## トラブルシューティング

### よくある問題と解決方法

#### 1. 権限エラー
```
Error: Access Denied: BigQuery BigQuery: Permission denied
```
**解決方法:** IAM権限の確認、サービスアカウントキーの更新

#### 2. クエリタイムアウト
```
Error: Query exceeded timeout
```
**解決方法:** クエリの最適化、パーティション使用、LIMIT句の追加

#### 3. スキーマエラー
```
Error: Invalid schema update
```
**解決方法:** データ型の確認、NULLABLEの設定確認

詳細なトラブルシューティングは[トラブルシューティングガイド](../operations/troubleshooting.md)を参照してください。

---

## 次のステップ

BigQueryのセットアップが完了したら：

1. [Supabaseセットアップ](supabase.md) - メインDB設定の確認
2. [環境設定](environment.md) - 統合環境変数設定
3. [API仕様書](../api/reference.md) - データ連携API開発

## 参考リンク

- [BigQuery公式ドキュメント](https://cloud.google.com/bigquery/docs)
- [BigQuery料金](https://cloud.google.com/bigquery/pricing)
- [BigQueryベストプラクティス](https://cloud.google.com/bigquery/docs/best-practices-performance-overview)