-- Supabase Auth.usersの削除を可能にするための修正（簡易版）
-- authスキーマのテーブルは変更できないため、publicスキーマのみ修正

-- 1. publicスキーマのテーブルのみ修正
-- profilesテーブル（最も重要）
ALTER TABLE public.profiles 
DROP CONSTRAINT IF EXISTS profiles_id_fkey;

ALTER TABLE public.profiles 
ADD CONSTRAINT profiles_id_fkey 
FOREIGN KEY (id) REFERENCES auth.users(id) ON DELETE CASCADE;

-- notification_settings
ALTER TABLE public.notification_settings 
DROP CONSTRAINT IF EXISTS notification_settings_user_id_fkey;

ALTER TABLE public.notification_settings 
ADD CONSTRAINT notification_settings_user_id_fkey 
FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;

-- jobs テーブル
ALTER TABLE public.jobs 
DROP CONSTRAINT IF EXISTS jobs_created_by_fkey;

ALTER TABLE public.jobs 
ADD CONSTRAINT jobs_created_by_fkey 
FOREIGN KEY (created_by) REFERENCES auth.users(id) ON DELETE SET NULL;

-- 2. 特定のユーザーを安全に削除する関数
-- publicスキーマのデータのみクリーンアップ
CREATE OR REPLACE FUNCTION delete_user_public_data(target_user_id UUID)
RETURNS void AS $$
BEGIN
    -- publicスキーマの関連データを削除
    DELETE FROM public.notification_settings WHERE user_id = target_user_id;
    DELETE FROM public.profiles WHERE id = target_user_id;
    UPDATE public.jobs SET created_by = NULL WHERE created_by = target_user_id;
    
    -- 他のテーブルでprofilesを参照している場合も処理
    UPDATE public.job_requirements SET created_by = NULL WHERE created_by = target_user_id;
    UPDATE public.searches SET created_by = NULL WHERE created_by = target_user_id;
    UPDATE public.candidates SET scraped_by = NULL WHERE scraped_by = target_user_id;
    
    -- submitted_byカラムが存在する場合のみ更新
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'candidate_submissions' 
        AND column_name = 'submitted_by'
    ) THEN
        UPDATE public.candidate_submissions SET submitted_by = NULL WHERE submitted_by = target_user_id;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- 3. ユーザー削除前の依存関係確認（publicスキーマのみ）
CREATE OR REPLACE FUNCTION check_user_public_dependencies(target_user_id UUID)
RETURNS TABLE (
    table_name TEXT,
    count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 'profiles'::TEXT, COUNT(*) FROM public.profiles WHERE id = target_user_id
    UNION ALL
    SELECT 'notification_settings'::TEXT, COUNT(*) FROM public.notification_settings WHERE user_id = target_user_id
    UNION ALL
    SELECT 'jobs (created_by)'::TEXT, COUNT(*) FROM public.jobs WHERE created_by = target_user_id
    UNION ALL
    SELECT 'job_requirements (created_by)'::TEXT, COUNT(*) FROM public.job_requirements WHERE created_by = target_user_id
    UNION ALL
    SELECT 'searches (created_by)'::TEXT, COUNT(*) FROM public.searches WHERE created_by = target_user_id
    UNION ALL
    SELECT 'candidates (scraped_by)'::TEXT, COUNT(*) FROM public.candidates WHERE scraped_by = target_user_id;
END;
$$ LANGUAGE plpgsql;

-- 使用手順：
-- 1. まず依存関係を確認
-- SELECT * FROM check_user_public_dependencies('user-uuid-here');

-- 2. publicスキーマのデータをクリーンアップ
-- SELECT delete_user_public_data('user-uuid-here');

-- 3. その後、Supabase DashboardからAuth.usersを削除

-- 注意：authスキーマのテーブル（identities, sessions等）は
-- Supabaseが自動的に管理するため、手動での変更は不要です。