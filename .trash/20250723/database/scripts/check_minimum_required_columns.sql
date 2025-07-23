-- job_requirementsテーブルの最小限必要なカラムを確認

-- 必須カラムの存在確認
SELECT 
    column_name,
    data_type,
    is_nullable,
    CASE 
        WHEN column_name IN ('id', 'client_id', 'title', 'description', 'structured_data', 'created_by') 
        THEN '必須'
        ELSE 'オプション'
    END as requirement_status
FROM information_schema.columns
WHERE table_schema = 'public' 
AND table_name = 'job_requirements'
ORDER BY 
    CASE 
        WHEN column_name IN ('id', 'client_id', 'title', 'description', 'structured_data', 'created_by') 
        THEN 0 
        ELSE 1 
    END,
    ordinal_position;

-- 最小限必要なカラムが全て存在するか確認
WITH required_columns AS (
    SELECT unnest(ARRAY['id', 'client_id', 'title', 'description', 'structured_data', 'created_by']) as column_name
),
existing_columns AS (
    SELECT column_name
    FROM information_schema.columns
    WHERE table_schema = 'public' 
    AND table_name = 'job_requirements'
)
SELECT 
    rc.column_name,
    CASE 
        WHEN ec.column_name IS NOT NULL THEN '✓ 存在'
        ELSE '✗ 不足'
    END as status
FROM required_columns rc
LEFT JOIN existing_columns ec ON rc.column_name = ec.column_name;

-- created_byの参照先確認（profilesかusersか）
SELECT 
    kcu.column_name,
    ccu.table_name AS references_table,
    ccu.column_name AS references_column
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY' 
AND tc.table_schema = 'public'
AND tc.table_name = 'job_requirements'
AND kcu.column_name = 'created_by';