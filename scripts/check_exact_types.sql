-- Supabaseの実際のテーブル型を確認するSQL
-- このクエリをSupabase SQL Editorで実行してください

SELECT 
    table_name,
    column_name,
    data_type,
    udt_name,  -- 実際の型名
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public' 
AND column_name = 'id'
AND table_name IN ('profiles', 'clients', 'job_requirements', 'candidates', 'search_jobs', 'jobs', 'scraping_sessions')
ORDER BY table_name;