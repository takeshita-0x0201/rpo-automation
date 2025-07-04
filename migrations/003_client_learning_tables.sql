-- BigQuery用テーブル作成スクリプト
-- クライアント企業別の学習データとパターンを管理

-- クライアント別採用パターン
CREATE TABLE IF NOT EXISTS client_learning.client_patterns (
    id STRING NOT NULL,
    client_id STRING NOT NULL,
    pattern_type STRING,  -- 'terminology', 'preference', 'criteria'
    pattern_name STRING,
    pattern_data JSON,
    usage_count INT64 DEFAULT 0,
    last_used_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP
)
PARTITION BY DATE(created_at)
CLUSTER BY client_id, pattern_type;

-- 採用成功事例（フィードバックデータ）
CREATE TABLE IF NOT EXISTS client_learning.successful_hires (
    id STRING NOT NULL,
    client_id STRING NOT NULL,
    candidate_id STRING NOT NULL,
    requirement_id STRING NOT NULL,
    search_id STRING NOT NULL,
    hired_date DATE,
    feedback_score INT64,  -- 1-5
    feedback_comments STRING,
    key_factors ARRAY<STRING>,  -- 採用決定の主要因
    candidate_attributes JSON,  -- 採用時点の候補者属性
    requirement_snapshot JSON,  -- 採用時点の要件
    created_at TIMESTAMP NOT NULL
)
PARTITION BY hired_date
CLUSTER BY client_id;

-- クライアントフィードバック履歴
CREATE TABLE IF NOT EXISTS client_learning.feedback_history (
    id STRING NOT NULL,
    client_id STRING NOT NULL,
    candidate_id STRING NOT NULL,
    search_id STRING NOT NULL,
    feedback_type STRING,  -- 'positive', 'negative', 'neutral'
    feedback_category STRING,  -- 'skills_match', 'experience', 'culture_fit', etc.
    feedback_text STRING,
    ai_score_at_time FLOAT64,
    human_score INT64,  -- 1-100
    created_by STRING,
    created_at TIMESTAMP NOT NULL
)
PARTITION BY DATE(created_at)
CLUSTER BY client_id, feedback_type;

-- クライアント別重要キーワード
CREATE TABLE IF NOT EXISTS client_learning.important_keywords (
    id STRING NOT NULL,
    client_id STRING NOT NULL,
    keyword STRING NOT NULL,
    keyword_type STRING,  -- 'skill', 'qualification', 'experience', 'other'
    importance_score FLOAT64,  -- 0.0-1.0
    positive_correlation BOOLEAN,  -- true: 持っていると良い, false: 持っていないと良い
    usage_contexts ARRAY<STRING>,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP
)
PARTITION BY DATE(created_at)
CLUSTER BY client_id;

-- AI判定精度追跡
CREATE TABLE IF NOT EXISTS client_learning.ai_accuracy_tracking (
    id STRING NOT NULL,
    client_id STRING NOT NULL,
    evaluation_period_start DATE,
    evaluation_period_end DATE,
    total_evaluations INT64,
    accurate_predictions INT64,  -- 人間の判断と一致した数
    false_positives INT64,  -- AIは良いと判断したが人間は否定
    false_negatives INT64,  -- AIは悪いと判断したが人間は肯定
    accuracy_rate FLOAT64,
    precision_rate FLOAT64,
    recall_rate FLOAT64,
    f1_score FLOAT64,
    calculated_at TIMESTAMP NOT NULL
)
PARTITION BY evaluation_period_start
CLUSTER BY client_id;

-- 学習用プロンプトテンプレート
CREATE TABLE IF NOT EXISTS client_learning.prompt_templates (
    id STRING NOT NULL,
    client_id STRING,  -- NULLの場合は汎用テンプレート
    template_name STRING NOT NULL,
    template_type STRING,  -- 'evaluation', 'structuring', 'summarization'
    template_content STRING,
    variables ARRAY<STRING>,  -- 使用する変数名のリスト
    performance_score FLOAT64,  -- このテンプレートの成功率
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP
)
PARTITION BY DATE(created_at);

-- ビュー作成: クライアント別の最新パフォーマンス
CREATE OR REPLACE VIEW client_learning.client_performance_summary AS
SELECT 
    c.client_id,
    c.client_name,
    COUNT(DISTINCT s.id) as total_searches,
    COUNT(DISTINCT can.id) as total_candidates,
    AVG(e.ai_score) as avg_ai_score,
    COUNT(DISTINCT sh.id) as successful_hires,
    AVG(at.accuracy_rate) as avg_accuracy_rate,
    MAX(s.started_at) as last_search_date
FROM 
    recruitment_data.searches s
    JOIN recruitment_data.candidates can ON s.id = can.search_id
    JOIN recruitment_data.ai_evaluations e ON can.id = e.candidate_id
    LEFT JOIN client_learning.successful_hires sh ON can.id = sh.candidate_id
    LEFT JOIN client_learning.ai_accuracy_tracking at ON s.client_id = at.client_id
    LEFT JOIN (
        SELECT DISTINCT client_id, name as client_name 
        FROM recruitment_data.requirements
    ) c ON s.client_id = c.client_id
WHERE 
    s.started_at >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
GROUP BY 
    c.client_id, c.client_name;