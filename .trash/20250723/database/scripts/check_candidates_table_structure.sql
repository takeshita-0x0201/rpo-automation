-- candidatesテーブルとscraping_sessionsテーブルの構造を確認するSQL
-- Supabase SQL Editorで実行してください

-- candidatesテーブルの構造
SELECT 
    column_name,
    data_type,
    udt_name,
    is_nullable,
    column_default,
    character_maximum_length
FROM information_schema.columns
WHERE table_schema = 'public' 
AND table_name = 'candidates'
ORDER BY ordinal_position;

-- scraping_sessionsテーブルの構造
SELECT 
    column_name,
    data_type,
    udt_name,
    is_nullable,
    column_default,
    character_maximum_length
FROM information_schema.columns
WHERE table_schema = 'public' 
AND table_name = 'scraping_sessions'
ORDER BY ordinal_position;

-- 外部キー制約の確認
SELECT
    tc.table_name, 
    kcu.column_name, 
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name,
    tc.constraint_name
FROM 
    information_schema.table_constraints AS tc 
    JOIN information_schema.key_column_usage AS kcu
      ON tc.constraint_name = kcu.constraint_name
      AND tc.table_schema = kcu.table_schema
    JOIN information_schema.constraint_column_usage AS ccu
      ON ccu.constraint_name = tc.constraint_name
      AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY' 
AND tc.table_name IN ('candidates', 'scraping_sessions');