-- RPO Automation データベース構造チェッククエリ
-- 必要なテーブルとカラムが全て存在しているかを確認

-- 1. テーブルの存在確認
WITH required_tables AS (
    SELECT unnest(ARRAY[
        'profiles',
        'clients',
        'requirements',
        'candidates',
        'search_jobs',
        'search_results',
        'candidate_submissions',
        'client_settings',
        'job_status_history',
        'notification_settings',
        'retry_queue'
    ]) AS table_name
),
existing_tables AS (
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'public'
    AND table_type = 'BASE TABLE'
)
SELECT 
    rt.table_name,
    CASE 
        WHEN et.table_name IS NOT NULL THEN '✅ 存在'
        ELSE '❌ 不足'
    END AS status
FROM required_tables rt
LEFT JOIN existing_tables et ON rt.table_name = et.table_name
ORDER BY 
    CASE WHEN et.table_name IS NULL THEN 0 ELSE 1 END,
    rt.table_name;

-- 2. 各テーブルの詳細構造確認
SELECT 
    '=== ' || table_name || ' テーブルの構造 ===' AS info
FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN (
    'profiles', 'clients', 'requirements', 'candidates', 
    'search_jobs', 'search_results', 'candidate_submissions'
)
ORDER BY table_name;

-- 3. 重要なカラムの存在確認
WITH required_columns AS (
    -- profiles テーブル
    SELECT 'profiles' AS table_name, 'id' AS column_name, 'uuid' AS expected_type
    UNION ALL SELECT 'profiles', 'email', 'text'
    UNION ALL SELECT 'profiles', 'role', 'text'
    UNION ALL SELECT 'profiles', 'status', 'text'
    
    -- clients テーブル
    UNION ALL SELECT 'clients', 'id', 'uuid'
    UNION ALL SELECT 'clients', 'name', 'text'
    UNION ALL SELECT 'clients', 'company_id', 'text'
    UNION ALL SELECT 'clients', 'allows_direct_scraping', 'boolean'
    
    -- requirements テーブル
    UNION ALL SELECT 'requirements', 'id', 'text'
    UNION ALL SELECT 'requirements', 'client_id', 'uuid'
    UNION ALL SELECT 'requirements', 'position_name', 'text'
    UNION ALL SELECT 'requirements', 'required_skills', 'text[]'
    UNION ALL SELECT 'requirements', 'status', 'text'
    
    -- candidates テーブル
    UNION ALL SELECT 'candidates', 'id', 'uuid'
    UNION ALL SELECT 'candidates', 'external_id', 'text'
    UNION ALL SELECT 'candidates', 'source', 'text'
    UNION ALL SELECT 'candidates', 'profile_data', 'jsonb'
    
    -- search_jobs テーブル
    UNION ALL SELECT 'search_jobs', 'id', 'uuid'
    UNION ALL SELECT 'search_jobs', 'requirement_id', 'text'
    UNION ALL SELECT 'search_jobs', 'client_id', 'uuid'
    UNION ALL SELECT 'search_jobs', 'status', 'text'
    
    -- search_results テーブル
    UNION ALL SELECT 'search_results', 'id', 'uuid'
    UNION ALL SELECT 'search_results', 'search_job_id', 'uuid'
    UNION ALL SELECT 'search_results', 'candidate_id', 'uuid'
    UNION ALL SELECT 'search_results', 'match_score', 'numeric'
    UNION ALL SELECT 'search_results', 'status', 'text'
),
actual_columns AS (
    SELECT 
        c.table_name,
        c.column_name,
        c.data_type,
        c.udt_name
    FROM information_schema.columns c
    WHERE c.table_schema = 'public'
)
SELECT 
    rc.table_name,
    rc.column_name,
    rc.expected_type AS "期待される型",
    COALESCE(ac.data_type, '❌ カラムなし') AS "実際の型",
    CASE 
        WHEN ac.column_name IS NULL THEN '❌ 不足'
        WHEN ac.data_type LIKE '%' || rc.expected_type || '%' OR ac.udt_name = rc.expected_type THEN '✅ OK'
        ELSE '⚠️  型が異なる'
    END AS status
FROM required_columns rc
LEFT JOIN actual_columns ac 
    ON rc.table_name = ac.table_name 
    AND rc.column_name = ac.column_name
ORDER BY 
    rc.table_name,
    CASE WHEN ac.column_name IS NULL THEN 0 ELSE 1 END,
    rc.column_name;

-- 4. 外部キー制約の確認
SELECT 
    tc.table_name AS "テーブル",
    kcu.column_name AS "カラム",
    ccu.table_name AS "参照先テーブル",
    ccu.column_name AS "参照先カラム"
FROM information_schema.table_constraints AS tc 
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
    AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY' 
AND tc.table_schema = 'public'
AND tc.table_name IN (
    'requirements', 'candidates', 'search_jobs', 'search_results'
)
ORDER BY tc.table_name, kcu.column_name;

-- 5. インデックスの確認
SELECT 
    schemaname,
    tablename AS "テーブル",
    indexname AS "インデックス名",
    indexdef AS "定義"
FROM pg_indexes
WHERE schemaname = 'public'
AND tablename IN (
    'requirements', 'candidates', 'search_jobs', 'search_results'
)
ORDER BY tablename, indexname;

-- 6. 総合診断結果
WITH diagnosis AS (
    SELECT 
        COUNT(*) FILTER (WHERE table_name IN ('requirements', 'candidates', 'search_results') 
            AND status = '❌ 不足') AS missing_tables,
        COUNT(*) FILTER (WHERE table_name IN ('profiles', 'clients', 'search_jobs') 
            AND status = '✅ 存在') AS existing_core_tables
    FROM (
        SELECT 
            rt.table_name,
            CASE WHEN et.table_name IS NOT NULL THEN '✅ 存在' ELSE '❌ 不足' END AS status
        FROM (
            SELECT unnest(ARRAY[
                'profiles', 'clients', 'requirements', 
                'candidates', 'search_jobs', 'search_results'
            ]) AS table_name
        ) rt
        LEFT JOIN (
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
        ) et ON rt.table_name = et.table_name
    ) t
)
SELECT 
    '=== 診断結果 ===' AS info,
    CASE 
        WHEN missing_tables = 0 THEN '✅ 全ての必要なテーブルが存在します'
        ELSE '❌ ' || missing_tables || '個の必要なテーブルが不足しています'
    END AS result
FROM diagnosis;