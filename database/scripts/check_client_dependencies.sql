-- クライアントテーブルに依存する全ての外部キー制約を確認

-- 1. clientsテーブルを参照している全ての外部キー制約を表示
SELECT 
    tc.table_name AS dependent_table,
    kcu.column_name AS dependent_column,
    tc.constraint_name,
    rc.delete_rule,
    rc.update_rule
FROM 
    information_schema.table_constraints AS tc 
    JOIN information_schema.key_column_usage AS kcu
      ON tc.constraint_name = kcu.constraint_name
      AND tc.table_schema = kcu.table_schema
    JOIN information_schema.constraint_column_usage AS ccu
      ON ccu.constraint_name = tc.constraint_name
      AND ccu.table_schema = tc.table_schema
    JOIN information_schema.referential_constraints AS rc
      ON tc.constraint_name = rc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY' 
  AND ccu.table_name = 'clients'
ORDER BY tc.table_name;

-- 2. 各テーブルごとのレコード数も確認
WITH client_dependencies AS (
    SELECT DISTINCT tc.table_name AS dependent_table
    FROM information_schema.table_constraints AS tc 
    JOIN information_schema.constraint_column_usage AS ccu
      ON ccu.constraint_name = tc.constraint_name
    WHERE tc.constraint_type = 'FOREIGN KEY' 
      AND ccu.table_name = 'clients'
)
SELECT 
    dependent_table,
    (SELECT COUNT(*) FROM information_schema.tables WHERE table_name = dependent_table) as table_exists
FROM client_dependencies
ORDER BY dependent_table;

-- 3. 特定のクライアントIDに関連するレコード数を確認する関数
CREATE OR REPLACE FUNCTION check_client_dependencies(target_client_id UUID)
RETURNS TABLE (
    table_name TEXT,
    record_count BIGINT
) AS $$
BEGIN
    -- job_requirements
    RETURN QUERY
    SELECT 'job_requirements'::TEXT, COUNT(*)::BIGINT
    FROM job_requirements
    WHERE client_id = target_client_id;

    -- candidates
    RETURN QUERY
    SELECT 'candidates'::TEXT, COUNT(*)::BIGINT
    FROM candidates
    WHERE client_id = target_client_id;

    -- scraping_sessions
    RETURN QUERY
    SELECT 'scraping_sessions'::TEXT, COUNT(*)::BIGINT
    FROM scraping_sessions
    WHERE client_id = target_client_id;

    -- job_postings（もし存在する場合）
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'job_postings') THEN
        RETURN QUERY
        EXECUTE format('SELECT ''job_postings''::TEXT, COUNT(*)::BIGINT FROM job_postings WHERE client_id = %L', target_client_id);
    END IF;
END;
$$ LANGUAGE plpgsql;

-- 使用例：特定のクライアントの依存関係を確認
-- SELECT * FROM check_client_dependencies('ここにクライアントIDを入れる'::UUID);