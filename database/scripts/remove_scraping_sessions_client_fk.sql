-- スクレイピングセッションテーブルのクライアント外部キー制約を削除
-- スクレイピングセッションはログ的な性質のため、クライアントが削除されても残すべき

-- 1. 外部キー制約の確認（どのような名前で作成されているか確認）
SELECT 
    tc.constraint_name, 
    tc.constraint_type,
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM 
    information_schema.table_constraints AS tc 
    JOIN information_schema.key_column_usage AS kcu
      ON tc.constraint_name = kcu.constraint_name
      AND tc.table_schema = kcu.table_schema
    JOIN information_schema.constraint_column_usage AS ccu
      ON ccu.constraint_name = tc.constraint_name
      AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY' 
  AND tc.table_name = 'scraping_sessions'
  AND ccu.table_name = 'clients';

-- 2. scraping_sessionsテーブルの構造を確認
\d scraping_sessions

-- 3. 外部キー制約を削除（制約名は上記のクエリで確認した名前を使用）
-- 一般的な命名規則に基づいて試す
DO $$ 
BEGIN
    -- パターン1: scraping_sessions_client_id_fkey
    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'scraping_sessions_client_id_fkey' 
        AND table_name = 'scraping_sessions'
    ) THEN
        ALTER TABLE scraping_sessions DROP CONSTRAINT scraping_sessions_client_id_fkey;
        RAISE NOTICE 'Dropped constraint: scraping_sessions_client_id_fkey';
    END IF;

    -- パターン2: fk_scraping_sessions_client
    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'fk_scraping_sessions_client' 
        AND table_name = 'scraping_sessions'
    ) THEN
        ALTER TABLE scraping_sessions DROP CONSTRAINT fk_scraping_sessions_client;
        RAISE NOTICE 'Dropped constraint: fk_scraping_sessions_client';
    END IF;

    -- パターン3: 他の命名パターン（実際の制約名を見つけて削除）
    FOR r IN (
        SELECT tc.constraint_name
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
    ) LOOP
        EXECUTE format('ALTER TABLE scraping_sessions DROP CONSTRAINT %I', r.constraint_name);
        RAISE NOTICE 'Dropped constraint: %', r.constraint_name;
    END LOOP;
END $$;

-- 4. 削除後の確認
SELECT 
    tc.constraint_name, 
    tc.constraint_type,
    tc.table_name,
    kcu.column_name
FROM 
    information_schema.table_constraints AS tc 
    JOIN information_schema.key_column_usage AS kcu
      ON tc.constraint_name = kcu.constraint_name
      AND tc.table_schema = kcu.table_schema
WHERE tc.table_name = 'scraping_sessions'
  AND tc.constraint_type = 'FOREIGN KEY';

-- 5. コメントを追加
COMMENT ON COLUMN scraping_sessions.client_id IS 'クライアントID（外部キー制約なし - ログ保持のため）';