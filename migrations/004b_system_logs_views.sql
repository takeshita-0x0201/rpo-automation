-- BigQuery用ビュー作成スクリプト
-- システムログの集計ビュー

-- 日次集計用ビュー
CREATE OR REPLACE VIEW system_logs.daily_system_stats AS
SELECT 
    DATE(COALESCE(al.timestamp, sl.timestamp, pm.timestamp, el.timestamp)) as date,
    COUNT(DISTINCT al.user_id) as active_users,
    COUNT(DISTINCT sl.job_id) as total_jobs,
    SUM(CASE WHEN sl.action = 'extract' THEN sl.extracted_count ELSE 0 END) as total_candidates_extracted,
    AVG(CASE WHEN pm.metric_type = 'api_latency' THEN pm.metric_value END) as avg_api_latency_ms,
    AVG(CASE WHEN pm.metric_type = 'scraping_speed' THEN pm.metric_value END) as avg_scraping_duration_s,
    COUNT(CASE WHEN el.error_level = 'error' THEN 1 END) as error_count,
    COUNT(CASE WHEN el.error_level = 'critical' THEN 1 END) as critical_error_count
FROM 
    system_logs.api_access_logs al
    FULL OUTER JOIN system_logs.scraping_logs sl ON DATE(al.timestamp) = DATE(sl.timestamp)
    FULL OUTER JOIN system_logs.performance_metrics pm ON DATE(al.timestamp) = DATE(pm.timestamp)
    FULL OUTER JOIN system_logs.error_logs el ON DATE(al.timestamp) = DATE(el.timestamp)
WHERE 
    DATE(COALESCE(al.timestamp, sl.timestamp, pm.timestamp, el.timestamp)) >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY 
    date;

-- アラート用ビュー: 直近1時間のクリティカルエラー
CREATE OR REPLACE VIEW system_logs.recent_critical_errors AS
SELECT 
    timestamp,
    error_type,
    error_message,
    context,
    job_id,
    user_id
FROM 
    system_logs.error_logs
WHERE 
    error_level = 'critical'
    AND resolved = false
    AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)
ORDER BY 
    timestamp DESC;