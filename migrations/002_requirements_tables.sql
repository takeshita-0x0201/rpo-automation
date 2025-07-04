-- BigQuery用テーブル作成スクリプト
-- 採用要件と検索結果を管理するテーブル

-- Supabaseに保存される要件の基本情報（BigQuery側のビュー）
CREATE TABLE IF NOT EXISTS recruitment_data.requirements (
    id STRING NOT NULL,
    client_id STRING NOT NULL,
    title STRING,
    position STRING,
    description STRING,
    required_skills ARRAY<STRING>,
    preferred_skills ARRAY<STRING>,
    experience_years INT64,
    education_level STRING,
    salary_range STRUCT<
        min INT64,
        max INT64,
        currency STRING
    >,
    work_location STRING,
    employment_type STRING,
    original_text STRING,
    structured_data JSON,
    created_at TIMESTAMP NOT NULL,
    created_by STRING,
    updated_at TIMESTAMP,
    status STRING
)
PARTITION BY DATE(created_at)
CLUSTER BY client_id, status;

-- 検索実行履歴
CREATE TABLE IF NOT EXISTS recruitment_data.searches (
    id STRING NOT NULL,
    requirement_id STRING NOT NULL,
    job_id STRING,  -- Supabase jobs.id への参照
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    status STRING,
    execution_mode STRING,  -- 'direct' or 'agent'
    total_candidates INT64,
    error_message STRING,
    search_params JSON,
    created_by STRING
)
PARTITION BY DATE(started_at)
CLUSTER BY requirement_id, status;

-- 候補者情報
CREATE TABLE IF NOT EXISTS recruitment_data.candidates (
    id STRING NOT NULL,
    search_id STRING NOT NULL,
    bizreach_id STRING,
    name STRING,
    current_title STRING,
    current_company STRING,
    experience_years INT64,
    skills ARRAY<STRING>,
    education STRING,
    profile_url STRING,
    profile_summary STRING,
    scraped_data JSON,
    scraped_at TIMESTAMP NOT NULL
)
PARTITION BY DATE(scraped_at)
CLUSTER BY search_id;

-- AI評価結果
CREATE TABLE IF NOT EXISTS recruitment_data.ai_evaluations (
    id STRING NOT NULL,
    candidate_id STRING NOT NULL,
    requirement_id STRING NOT NULL,
    search_id STRING NOT NULL,
    ai_score FLOAT64,
    match_reasons ARRAY<STRING>,
    concerns ARRAY<STRING>,
    recommendation STRING,  -- 'highly_recommended', 'recommended', 'neutral', 'not_recommended'
    detailed_evaluation JSON,
    evaluated_at TIMESTAMP NOT NULL,
    model_version STRING,
    prompt_version STRING
)
PARTITION BY DATE(evaluated_at)
CLUSTER BY search_id, recommendation;

-- 要件ドキュメント（原本管理）
CREATE TABLE IF NOT EXISTS recruitment_data.requirement_documents (
    id STRING NOT NULL,
    requirement_id STRING NOT NULL,
    filename STRING,
    content_type STRING,
    original_text STRING,
    structured_by_ai BOOLEAN,
    ai_structured_data JSON,
    uploaded_by STRING,
    uploaded_at TIMESTAMP NOT NULL
)
PARTITION BY DATE(uploaded_at);

-- インデックス作成（BigQueryでは不要だが、ドキュメントとして記載）
-- BigQueryは自動的にクラスタリングキーでインデックスを最適化します