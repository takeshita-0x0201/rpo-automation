-- BigQuery用ストアドプロシージャとUDF
-- データ処理の効率化と標準化のための関数群

-- 採用要件の構造化データを正規化する関数
CREATE OR REPLACE FUNCTION recruitment_data.normalize_requirement_data(
    raw_data JSON
)
RETURNS JSON
LANGUAGE js AS """
    // 入力データの正規化
    const normalized = {
        required_skills: [],
        preferred_skills: [],
        experience_years: null,
        education_level: null,
        salary_range: {min: null, max: null, currency: 'JPY'}
    };
    
    try {
        const data = JSON.parse(raw_data);
        
        // スキルの正規化（重複除去、小文字化）
        if (data.required_skills) {
            normalized.required_skills = [...new Set(
                data.required_skills.map(s => s.toLowerCase().trim())
            )];
        }
        
        if (data.preferred_skills) {
            normalized.preferred_skills = [...new Set(
                data.preferred_skills.map(s => s.toLowerCase().trim())
            )];
        }
        
        // 経験年数の正規化
        normalized.experience_years = parseInt(data.experience_years) || 0;
        
        // 給与レンジの正規化
        if (data.salary_range) {
            normalized.salary_range = {
                min: parseInt(data.salary_range.min) || null,
                max: parseInt(data.salary_range.max) || null,
                currency: data.salary_range.currency || 'JPY'
            };
        }
        
        return JSON.stringify(normalized);
    } catch (e) {
        return JSON.stringify(normalized);
    }
""";

-- AI評価スコアの正規化（0-100の範囲に収める）
CREATE OR REPLACE FUNCTION recruitment_data.normalize_ai_score(
    raw_score FLOAT64
)
RETURNS FLOAT64
AS (
    CASE 
        WHEN raw_score < 0 THEN 0
        WHEN raw_score > 100 THEN 100
        ELSE raw_score
    END
);

-- クライアント別の採用成功率を計算
CREATE OR REPLACE PROCEDURE client_learning.calculate_client_success_rate(
    IN client_id STRING,
    IN period_days INT64
)
OPTIONS(strict_mode=false)
BEGIN
    DECLARE success_rate FLOAT64;
    DECLARE total_candidates INT64;
    DECLARE successful_hires INT64;
    
    -- 期間内の候補者数と採用数を集計
    SET (total_candidates, successful_hires) = (
        SELECT AS STRUCT
            COUNT(DISTINCT c.id),
            COUNT(DISTINCT sh.candidate_id)
        FROM recruitment_data.candidates c
        JOIN recruitment_data.searches s ON c.search_id = s.id
        LEFT JOIN client_learning.successful_hires sh ON c.id = sh.candidate_id
        WHERE s.client_id = client_id
        AND s.started_at >= DATE_SUB(CURRENT_DATE(), INTERVAL period_days DAY)
    );
    
    -- 成功率の計算
    SET success_rate = IF(total_candidates > 0, 
        successful_hires / total_candidates * 100, 
        0
    );
    
    -- 結果をログに記録
    INSERT INTO client_learning.ai_accuracy_tracking (
        id,
        client_id,
        evaluation_period_start,
        evaluation_period_end,
        total_evaluations,
        accurate_predictions,
        accuracy_rate,
        calculated_at
    )
    VALUES (
        GENERATE_UUID(),
        client_id,
        DATE_SUB(CURRENT_DATE(), INTERVAL period_days DAY),
        CURRENT_DATE(),
        total_candidates,
        successful_hires,
        success_rate,
        CURRENT_TIMESTAMP()
    );
END;

-- 候補者データのクレンジング
CREATE OR REPLACE PROCEDURE recruitment_data.clean_candidate_data(
    IN search_id STRING
)
OPTIONS(strict_mode=false)
BEGIN
    -- 重複候補者の除去（同じBizreach IDを持つ最新のレコードのみ保持）
    DELETE FROM recruitment_data.candidates
    WHERE search_id = search_id
    AND id NOT IN (
        SELECT id
        FROM (
            SELECT id,
                   ROW_NUMBER() OVER (
                       PARTITION BY bizreach_id 
                       ORDER BY scraped_at DESC
                   ) as rn
            FROM recruitment_data.candidates
            WHERE search_id = search_id
        )
        WHERE rn = 1
    );
    
    -- 無効なデータの修正
    UPDATE recruitment_data.candidates
    SET 
        experience_years = GREATEST(0, experience_years),
        skills = ARRAY(
            SELECT DISTINCT LOWER(TRIM(skill))
            FROM UNNEST(skills) as skill
            WHERE LENGTH(TRIM(skill)) > 0
        )
    WHERE search_id = search_id;
END;

-- 日次バッチ処理: 古いデータのアーカイブ
CREATE OR REPLACE PROCEDURE system_logs.archive_old_logs()
OPTIONS(strict_mode=false)
BEGIN
    -- 90日以上前のAPIログをアーカイブテーブルに移動
    INSERT INTO system_logs.api_access_logs_archive
    SELECT * FROM system_logs.api_access_logs
    WHERE DATE(timestamp) < DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY);
    
    DELETE FROM system_logs.api_access_logs
    WHERE DATE(timestamp) < DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY);
    
    -- エラーログのアーカイブ（解決済みのもののみ）
    INSERT INTO system_logs.error_logs_archive
    SELECT * FROM system_logs.error_logs
    WHERE DATE(timestamp) < DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
    AND resolved = true;
    
    DELETE FROM system_logs.error_logs
    WHERE DATE(timestamp) < DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
    AND resolved = true;
END;

-- スケジュールドクエリ用: 日次レポート生成
CREATE OR REPLACE TABLE FUNCTION recruitment_data.generate_daily_report(
    report_date DATE
)
AS (
    SELECT 
        r.client_id,
        COUNT(DISTINCT s.id) as searches_count,
        COUNT(DISTINCT c.id) as candidates_count,
        AVG(e.ai_score) as avg_ai_score,
        COUNT(DISTINCT CASE WHEN e.recommendation = 'highly_recommended' THEN c.id END) as highly_recommended_count,
        COUNT(DISTINCT CASE WHEN e.recommendation = 'recommended' THEN c.id END) as recommended_count
    FROM recruitment_data.searches s
    JOIN recruitment_data.requirements r ON s.requirement_id = r.id
    JOIN recruitment_data.candidates c ON s.id = c.search_id
    JOIN recruitment_data.ai_evaluations e ON c.id = e.candidate_id
    WHERE DATE(s.started_at) = report_date
    GROUP BY r.client_id
);