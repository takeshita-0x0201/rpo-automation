-- BigQuery用テーブル作成スクリプト（テーブルのみ）
-- システムログと監査ログを管理

-- API アクセスログ
CREATE TABLE IF NOT EXISTS system_logs.api_access_logs (
    id STRING NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    user_id STRING,
    method STRING,  -- GET, POST, PUT, DELETE
    endpoint STRING,
    request_body JSON,
    response_status INT64,
    response_time_ms INT64,
    ip_address STRING,
    user_agent STRING,
    error_message STRING
)
PARTITION BY DATE(timestamp)
CLUSTER BY user_id, endpoint;

-- 監査ログ（全ての重要な操作を記録）
CREATE TABLE IF NOT EXISTS system_logs.audit_logs (
    id STRING NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    user_id STRING NOT NULL,
    action_type STRING,  -- 'create', 'update', 'delete', 'view', 'export'
    resource_type STRING,  -- 'requirement', 'candidate', 'client', 'job'
    resource_id STRING,
    changes JSON,  -- 変更前後の値
    ip_address STRING,
    session_id STRING,
    additional_context JSON
)
PARTITION BY DATE(timestamp)
CLUSTER BY user_id, resource_type, action_type;

-- エラーログ
CREATE TABLE IF NOT EXISTS system_logs.error_logs (
    id STRING NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    error_type STRING,  -- 'scraping', 'api', 'ai_evaluation', 'system'
    error_level STRING,  -- 'warning', 'error', 'critical'
    error_message STRING,
    stack_trace STRING,
    context JSON,  -- エラー発生時の状況
    job_id STRING,
    user_id STRING,
    resolved BOOLEAN DEFAULT false,
    resolved_at TIMESTAMP,
    resolution_notes STRING
)
PARTITION BY DATE(timestamp)
CLUSTER BY error_type, error_level;

-- スクレイピング実行ログ
CREATE TABLE IF NOT EXISTS system_logs.scraping_logs (
    id STRING NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    job_id STRING NOT NULL,
    search_id STRING,
    action STRING,  -- 'login', 'search', 'extract', 'paginate'
    target_url STRING,
    success BOOLEAN,
    duration_ms INT64,
    extracted_count INT64,
    error_message STRING,
    agent_id STRING,  -- エージェント識別子
    execution_mode STRING  -- 'direct' or 'agent'
)
PARTITION BY DATE(timestamp)
CLUSTER BY job_id, action;

-- パフォーマンスメトリクス
CREATE TABLE IF NOT EXISTS system_logs.performance_metrics (
    id STRING NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    metric_type STRING,  -- 'api_latency', 'scraping_speed', 'ai_evaluation_time'
    metric_name STRING,
    metric_value FLOAT64,
    unit STRING,  -- 'ms', 'seconds', 'count'
    dimensions JSON,  -- 追加の分析用ディメンション
    service STRING  -- 'webapp', 'cloud_function', 'agent'
)
PARTITION BY DATE(timestamp)
CLUSTER BY metric_type, service;

-- Pub/Sub メッセージログ
CREATE TABLE IF NOT EXISTS system_logs.pubsub_logs (
    id STRING NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    message_id STRING,
    topic STRING,
    subscription STRING,
    action STRING,  -- 'publish', 'receive', 'ack', 'nack'
    message_data JSON,
    attributes JSON,
    processing_time_ms INT64,
    success BOOLEAN,
    error_message STRING
)
PARTITION BY DATE(timestamp)
CLUSTER BY topic, action;