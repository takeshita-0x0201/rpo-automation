-- スクレイピングセッションテーブルの外部キー制約をCASCADE削除に更新
-- これにより、クライアントが削除されるとスクレイピングセッションも自動的に削除される

-- 1. 現在の外部キー制約を確認
SELECT 
    tc.constraint_name, 
    tc.constraint_type,
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name,
    rc.delete_rule
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
  AND tc.table_name = 'scraping_sessions'
  AND ccu.table_name = 'clients';

-- 2. 外部キー制約を削除して再作成（CASCADE付き）
DO $$ 
DECLARE
    constraint_name_var TEXT;
BEGIN
    -- 既存の外部キー制約名を取得
    SELECT tc.constraint_name INTO constraint_name_var
    FROM information_schema.table_constraints AS tc 
    JOIN information_schema.key_column_usage AS kcu
      ON tc.constraint_name = kcu.constraint_name
      AND tc.table_schema = kcu.table_schema
    JOIN information_schema.constraint_column_usage AS ccu
      ON ccu.constraint_name = tc.constraint_name
      AND ccu.table_schema = tc.table_schema
    WHERE tc.constraint_type = 'FOREIGN KEY' 
      AND tc.table_name = 'scraping_sessions'
      AND ccu.table_name = 'clients'
    LIMIT 1;

    -- 制約が存在する場合は削除
    IF constraint_name_var IS NOT NULL THEN
        EXECUTE format('ALTER TABLE scraping_sessions DROP CONSTRAINT %I', constraint_name_var);
        RAISE NOTICE 'Dropped existing constraint: %', constraint_name_var;
    END IF;

    -- 新しい制約をCASCADE削除で追加
    ALTER TABLE scraping_sessions 
    ADD CONSTRAINT scraping_sessions_client_id_fkey 
    FOREIGN KEY (client_id) 
    REFERENCES clients(id) 
    ON DELETE CASCADE;
    
    RAISE NOTICE 'Created new constraint with CASCADE delete';
END $$;

-- 3. 変更後の確認
SELECT 
    tc.constraint_name, 
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    rc.delete_rule
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
  AND tc.table_name = 'scraping_sessions'
  AND ccu.table_name = 'clients';