-- requirement_id関連の確認SQL

-- 1. requirement_idカラムの存在確認
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public' 
AND table_name = 'job_requirements'
AND column_name IN ('requirement_id', 'job_posting_id')
ORDER BY column_name;

-- 2. get_next_requirement_id関数の存在確認
SELECT 
    routine_name,
    routine_type,
    data_type
FROM information_schema.routines
WHERE routine_schema = 'public'
AND routine_name = 'get_next_requirement_id';

-- 3. requirement_sequencesテーブルの確認
SELECT * FROM requirement_sequences WHERE prefix = 'req';

-- 4. 現在の連番を確認（存在する場合）
SELECT current_number FROM requirement_sequences WHERE prefix = 'req';

-- 5. テスト実行（実際に連番を取得）
-- SELECT get_next_requirement_id();

-- 6. job_requirementsテーブルの全カラムを確認
SELECT 
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' 
AND table_name = 'job_requirements'
ORDER BY ordinal_position;