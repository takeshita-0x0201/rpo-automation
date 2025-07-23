-- BigQuery構成確認用SQL
-- RPO Automationのデータベース設計を確認するためのクエリ集

-- ==================================================
-- 1. データセット一覧の確認
-- ==================================================
SELECT
  schema_name as dataset_name,
  creation_time,
  last_modified_time
FROM
  `rpo-automation.INFORMATION_SCHEMA.SCHEMATA`
WHERE
  schema_name LIKE '%recruitment%' 
  OR schema_name LIKE '%rpo%'
ORDER BY
  schema_name;

-- ==================================================
-- 2. recruitment_dataデータセット内のテーブル一覧
-- ==================================================
SELECT
  table_name,
  table_type,
  creation_time,
  row_count,
  size_bytes
FROM
  `rpo-automation.recruitment_data.__TABLES__`
ORDER BY
  table_name;

-- ==================================================
-- 3. candidatesテーブルの詳細構造
-- ==================================================
SELECT
  column_name,
  data_type,
  is_nullable,
  is_partitioning_column,
  clustering_ordinal_position
FROM
  `rpo-automation.recruitment_data.INFORMATION_SCHEMA.COLUMNS`
WHERE
  table_name = 'candidates'
ORDER BY
  ordinal_position;

-- ==================================================
-- 4. candidatesテーブルのサンプルデータ（最新10件）
-- ==================================================
SELECT
  id,
  name,
  current_company,
  current_position,
  scraped_at,
  JSON_VALUE(scraped_data, '$.client_id') as client_id,
  JSON_VALUE(scraped_data, '$.session_id') as session_id
FROM
  `rpo-automation.recruitment_data.candidates`
ORDER BY
  scraped_at DESC
LIMIT 10;

-- ==================================================
-- 5. データの統計情報
-- ==================================================
-- 5.1 日別のデータ件数
SELECT
  DATE(scraped_at) as scrape_date,
  COUNT(*) as record_count,
  COUNT(DISTINCT id) as unique_candidates
FROM
  `rpo-automation.recruitment_data.candidates`
WHERE
  scraped_at >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY
  scrape_date
ORDER BY
  scrape_date DESC;

-- 5.2 クライアント別のデータ件数
SELECT
  JSON_VALUE(scraped_data, '$.client_id') as client_id,
  COUNT(*) as candidate_count
FROM
  `rpo-automation.recruitment_data.candidates`
WHERE
  scraped_at >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY
  client_id
ORDER BY
  candidate_count DESC;

-- ==================================================
-- 6. パーティションとクラスタリングの確認
-- ==================================================
SELECT
  table_name,
  partition_expiration_days,
  clustering_fields
FROM
  `rpo-automation.recruitment_data.INFORMATION_SCHEMA.TABLES`
WHERE
  table_name = 'candidates';

-- ==================================================
-- 7. scraped_dataのJSON構造確認（サンプル）
-- ==================================================
SELECT
  id,
  TO_JSON_STRING(scraped_data) as scraped_data_json
FROM
  `rpo-automation.recruitment_data.candidates`
WHERE
  scraped_data IS NOT NULL
LIMIT 1;

-- ==================================================
-- 8. 他の関連テーブルの確認
-- ==================================================
-- 8.1 AI評価結果テーブルの存在確認
SELECT
  table_name,
  creation_time,
  row_count
FROM
  `rpo-automation.recruitment_data.__TABLES__`
WHERE
  table_name IN ('ai_evaluations', 'searches', 'requirements');

-- ==================================================
-- 9. テーブルサイズと料金見積もり
-- ==================================================
SELECT
  table_name,
  ROUND(size_bytes / POW(10, 9), 2) as size_gb,
  ROUND(size_bytes / POW(10, 9) * 5, 2) as estimated_storage_cost_usd_per_month
FROM
  `rpo-automation.recruitment_data.__TABLES__`
ORDER BY
  size_bytes DESC;

-- ==================================================
-- 10. 最新のデータ取得日時
-- ==================================================
SELECT
  MAX(scraped_at) as latest_scraped_at,
  MIN(scraped_at) as oldest_scraped_at,
  DATE_DIFF(CURRENT_DATE(), DATE(MAX(scraped_at)), DAY) as days_since_last_scrape
FROM
  `rpo-automation.recruitment_data.candidates`;