-- Supabase Auth.usersの削除を可能にするための修正
-- 注意: この操作は管理者権限が必要です

-- 1. まず、auth.usersに依存している全ての外部キー制約を確認
-- このクエリで現在の制約を確認できます
/*
SELECT
    tc.table_schema, 
    tc.table_name, 
    tc.constraint_name, 
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
  AND ccu.table_name = 'users'
  AND ccu.table_schema = 'auth';
*/

-- 2. 最も重要な制約から修正を開始
-- profilesテーブル（これが最も一般的な問題）
ALTER TABLE public.profiles 
DROP CONSTRAINT IF EXISTS profiles_id_fkey;

ALTER TABLE public.profiles 
ADD CONSTRAINT profiles_id_fkey 
FOREIGN KEY (id) REFERENCES auth.users(id) ON DELETE CASCADE;

-- 3. その他のauth.usersを直接参照しているテーブルを修正
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

-- 4. auth schemaの内部テーブルも確認（Supabaseのバージョンによって異なる場合があります）
-- auth.identities
ALTER TABLE auth.identities
DROP CONSTRAINT IF EXISTS identities_user_id_fkey;

ALTER TABLE auth.identities
ADD CONSTRAINT identities_user_id_fkey
FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;

-- auth.sessions
ALTER TABLE auth.sessions
DROP CONSTRAINT IF EXISTS sessions_user_id_fkey;

ALTER TABLE auth.sessions
ADD CONSTRAINT sessions_user_id_fkey
FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;

-- auth.refresh_tokens
ALTER TABLE auth.refresh_tokens
DROP CONSTRAINT IF EXISTS refresh_tokens_user_id_fkey;

-- Supabaseの新しいバージョンではrefresh_tokensがsessionsに統合されている可能性があります
-- エラーが出る場合はこの部分をコメントアウトしてください

-- 5. auth.mfa_factors（多要素認証を使用している場合）
ALTER TABLE auth.mfa_factors
DROP CONSTRAINT IF EXISTS mfa_factors_user_id_fkey;

ALTER TABLE auth.mfa_factors
ADD CONSTRAINT mfa_factors_user_id_fkey
FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;

-- 6. auth.mfa_challenges（多要素認証を使用している場合）
ALTER TABLE auth.mfa_challenges
DROP CONSTRAINT IF EXISTS mfa_challenges_user_id_fkey;

ALTER TABLE auth.mfa_challenges
ADD CONSTRAINT mfa_challenges_user_id_fkey
FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;

-- 7. 一時的な解決策：特定のユーザーを削除する関数
-- この関数は関連データを手動でクリーンアップしてからユーザーを削除します
CREATE OR REPLACE FUNCTION delete_auth_user_safely(user_id UUID)
RETURNS void AS $$
BEGIN
    -- トランザクション内で実行
    -- publicスキーマのデータを削除
    DELETE FROM public.notification_settings WHERE user_id = user_id;
    DELETE FROM public.profiles WHERE id = user_id;
    
    -- authスキーマのデータを削除
    DELETE FROM auth.identities WHERE user_id = user_id;
    DELETE FROM auth.sessions WHERE user_id = user_id;
    DELETE FROM auth.mfa_factors WHERE user_id = user_id;
    DELETE FROM auth.mfa_challenges WHERE factor_id IN (SELECT id FROM auth.mfa_factors WHERE user_id = user_id);
    
    -- 最後にユーザーを削除
    DELETE FROM auth.users WHERE id = user_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 使用例：
-- SELECT delete_auth_user_safely('user-uuid-here');

-- 8. デバッグ用：特定のユーザーに関連するデータを確認
CREATE OR REPLACE FUNCTION check_user_dependencies(user_id UUID)
RETURNS TABLE (
    table_name TEXT,
    count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 'profiles'::TEXT, COUNT(*) FROM public.profiles WHERE id = user_id
    UNION ALL
    SELECT 'notification_settings'::TEXT, COUNT(*) FROM public.notification_settings WHERE user_id = user_id
    UNION ALL
    SELECT 'jobs'::TEXT, COUNT(*) FROM public.jobs WHERE created_by = user_id
    UNION ALL
    SELECT 'identities'::TEXT, COUNT(*) FROM auth.identities WHERE user_id = user_id
    UNION ALL
    SELECT 'sessions'::TEXT, COUNT(*) FROM auth.sessions WHERE user_id = user_id
    UNION ALL
    SELECT 'mfa_factors'::TEXT, COUNT(*) FROM auth.mfa_factors WHERE user_id = user_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 使用例：
-- SELECT * FROM check_user_dependencies('user-uuid-here');