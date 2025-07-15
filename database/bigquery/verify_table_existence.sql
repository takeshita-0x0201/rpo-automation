-- BigQueryテーブル存在確認と作成用SQL
-- candidatesテーブルが存在しない場合の作成スクリプト

-- ==================================================
-- 1. 簡易確認用クエリ（エラーが出たらテーブルが存在しない）
-- ==================================================
SELECT COUNT(*) as table_exists FROM `rpo-automation.recruitment_data.candidates` LIMIT 1;

-- ==================================================
-- 2. candidatesテーブルが存在しない場合の作成SQL
-- ==================================================
-- ※ 上記クエリでエラーが出た場合、以下を実行

-- 2.1 データセットの作成（存在しない場合）
CREATE SCHEMA IF NOT EXISTS `rpo-automation.recruitment_data`
OPTIONS(
  description="RPO Automation - 採用候補者データ",
  location="asia-northeast1"
);

-- 2.2 candidatesテーブルの作成
CREATE TABLE IF NOT EXISTS `rpo-automation.recruitment_data.candidates` (
  -- 基本情報
  id STRING NOT NULL,
  search_id STRING,
  session_id STRING,
  
  -- 候補者情報
  name STRING,
  bizreach_id STRING,
  bizreach_url STRING,
  current_title STRING,
  current_position STRING,
  current_company STRING,
  
  -- スキルと経験
  experience_years INT64,
  skills ARRAY<STRING>,
  education STRING,
  
  -- プロフィール
  profile_url STRING,
  profile_summary STRING,
  
  -- スクレイピング情報
  scraped_at TIMESTAMP NOT NULL,
  scraped_by STRING,
  platform STRING DEFAULT 'bizreach',
  
  -- 追加データ（JSON形式）
  scraped_data JSON,
  
  -- メタデータ
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY DATE(scraped_at)
CLUSTER BY search_id, current_company
OPTIONS(
  description = "BizReachからスクレイピングした候補者データ",
  partition_expiration_days = 180  -- 6ヶ月後に自動削除
);

-- ==================================================
-- 3. サンプルデータの挿入（テスト用）
-- ==================================================
-- ※ テーブル作成後、動作確認用のサンプルデータ

INSERT INTO `rpo-automation.recruitment_data.candidates` (
  id,
  search_id,
  session_id,
  name,
  current_company,
  current_position,
  experience_years,
  skills,
  education,
  scraped_at,
  scraped_by,
  scraped_data
) VALUES (
  GENERATE_UUID(),
  'test-search-001',
  'test-session-001',
  'テスト 太郎',
  '株式会社テスト',
  'シニアエンジニア',
  5,
  ['Python', 'Django', 'AWS'],
  '東京大学',
  CURRENT_TIMESTAMP(),
  'test-user',
  JSON '{
    "client_id": "test-client-001",
    "requirement_id": "test-req-001",
    "age": "30代前半",
    "current_salary": "600-800万円",
    "desired_location": "東京"
  }'
);

-- ==================================================
-- 4. 関連テーブルの作成（必要に応じて）
-- ==================================================

-- 4.1 AI評価結果テーブル
CREATE TABLE IF NOT EXISTS `rpo-automation.recruitment_data.ai_evaluations` (
  id STRING NOT NULL,
  candidate_id STRING NOT NULL,
  requirement_id STRING NOT NULL,
  search_id STRING,
  
  -- 評価結果
  ai_score FLOAT64,
  match_reasons ARRAY<STRING>,
  concerns ARRAY<STRING>,
  recommendation STRING,
  detailed_evaluation JSON,
  
  -- メタデータ
  evaluated_at TIMESTAMP NOT NULL,
  model_version STRING,
  prompt_version STRING
)
PARTITION BY DATE(evaluated_at)
CLUSTER BY search_id, recommendation
OPTIONS(
  description = "AI による候補者評価結果",
  partition_expiration_days = 365  -- 1年後に自動削除
);

-- 4.2 検索セッションテーブル
CREATE TABLE IF NOT EXISTS `rpo-automation.recruitment_data.searches` (
  id STRING NOT NULL,
  requirement_id STRING NOT NULL,
  client_id STRING NOT NULL,
  
  -- セッション情報
  started_at TIMESTAMP NOT NULL,
  completed_at TIMESTAMP,
  status STRING,
  execution_mode STRING,
  
  -- 結果
  total_candidates INT64,
  evaluated_candidates INT64,
  matched_candidates INT64,
  
  -- エラー情報
  error_message STRING,
  
  -- パラメータ
  search_params JSON,
  
  -- メタデータ
  created_by STRING,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY DATE(started_at)
OPTIONS(
  description = "検索/AIマッチングセッション情報"
);