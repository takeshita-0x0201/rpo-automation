-- job_requirementsテーブルのカラム構造を確認するSQL

-- 1. job_requirementsテーブルの全カラムを確認
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public' 
AND table_name = 'job_requirements'
ORDER BY ordinal_position;

-- 2. 必要なカラムの存在確認（結果が返ってくればカラムが存在）
SELECT 
    'job_posting_id' as column_name,
    EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'job_requirements' 
        AND column_name = 'job_posting_id'
    ) as exists
UNION ALL
SELECT 
    'job_description' as column_name,
    EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'job_requirements' 
        AND column_name = 'job_description'
    ) as exists
UNION ALL
SELECT 
    'memo' as column_name,
    EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'job_requirements' 
        AND column_name = 'memo'
    ) as exists;

-- 3. get_next_job_posting_id関数の存在確認
SELECT 
    routine_name,
    routine_type,
    data_type
FROM information_schema.routines
WHERE routine_schema = 'public'
AND routine_name = 'get_next_job_posting_id';

-- 4. job_posting_sequencesテーブルの存在確認
SELECT 
    table_name,
    EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name = 'job_posting_sequences'
    ) as exists
FROM (SELECT 'job_posting_sequences' as table_name) t;

-- 5. job_posting_sequencesテーブルの現在の値を確認
SELECT * FROM job_posting_sequences WHERE prefix = 'req';

-- 6. RLSポリシーの確認
SELECT 
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd,
    qual,
    with_check
FROM pg_policies
WHERE schemaname = 'public' 
AND tablename = 'job_requirements';

-- 7. created_byカラムの参照先を確認（profilesまたはusers）
SELECT 
    tc.constraint_name,
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
    AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY' 
AND tc.table_name = 'job_requirements'
AND kcu.column_name = 'created_by';

-- 8. サンプルデータで挿入テスト（実際のデータで置き換えてください）
-- 注意: 実際のclient_idとuser_idを使用してください
/*
INSERT INTO job_requirements (
    client_id,
    job_posting_id,
    title,
    description,
    job_description,
    memo,
    structured_data,
    created_by
) VALUES (
    'YOUR_CLIENT_UUID_HERE',  -- 実際のclient_idに置き換え
    'req-test-001',
    'テストポジション',
    'テスト説明',
    'テスト求人票',
    'テストメモ',
    '{}',
    'YOUR_USER_UUID_HERE'  -- 実際のuser_idに置き換え
);
*/