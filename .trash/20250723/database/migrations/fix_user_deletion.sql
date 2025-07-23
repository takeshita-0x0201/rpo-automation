-- ユーザー削除を可能にするための修正
-- 外部キー制約にON DELETE CASCADEを追加

-- 1. profilesテーブルの外部キー制約を更新
ALTER TABLE profiles 
DROP CONSTRAINT IF EXISTS profiles_id_fkey;

ALTER TABLE profiles 
ADD CONSTRAINT profiles_id_fkey 
FOREIGN KEY (id) REFERENCES auth.users(id) ON DELETE CASCADE;

-- 2. notification_settingsテーブルの外部キー制約を更新
ALTER TABLE notification_settings 
DROP CONSTRAINT IF EXISTS notification_settings_user_id_fkey;

ALTER TABLE notification_settings 
ADD CONSTRAINT notification_settings_user_id_fkey 
FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;

-- 3. jobsテーブルの外部キー制約を更新（created_byをNULLに設定）
ALTER TABLE jobs 
DROP CONSTRAINT IF EXISTS jobs_created_by_fkey;

ALTER TABLE jobs 
ADD CONSTRAINT jobs_created_by_fkey 
FOREIGN KEY (created_by) REFERENCES auth.users(id) ON DELETE SET NULL;

-- 4. job_requirementsテーブルの外部キー制約を更新
ALTER TABLE job_requirements 
DROP CONSTRAINT IF EXISTS job_requirements_created_by_fkey;

ALTER TABLE job_requirements 
ADD CONSTRAINT job_requirements_created_by_fkey 
FOREIGN KEY (created_by) REFERENCES profiles(id) ON DELETE SET NULL;

-- 5. searchesテーブルの外部キー制約を更新
ALTER TABLE searches 
DROP CONSTRAINT IF EXISTS searches_created_by_fkey;

ALTER TABLE searches 
ADD CONSTRAINT searches_created_by_fkey 
FOREIGN KEY (created_by) REFERENCES profiles(id) ON DELETE SET NULL;

-- 6. candidatesテーブルの外部キー制約を更新
ALTER TABLE candidates 
DROP CONSTRAINT IF EXISTS candidates_scraped_by_fkey;

ALTER TABLE candidates 
ADD CONSTRAINT candidates_scraped_by_fkey 
FOREIGN KEY (scraped_by) REFERENCES profiles(id) ON DELETE SET NULL;

-- 7. candidate_submissionsテーブルの外部キー制約を更新
-- submitted_byカラムが存在する場合のみ実行
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'candidate_submissions' 
        AND column_name = 'submitted_by'
    ) THEN
        ALTER TABLE candidate_submissions 
        DROP CONSTRAINT IF EXISTS candidate_submissions_submitted_by_fkey;
        
        ALTER TABLE candidate_submissions 
        ADD CONSTRAINT candidate_submissions_submitted_by_fkey 
        FOREIGN KEY (submitted_by) REFERENCES profiles(id) ON DELETE SET NULL;
    END IF;
END $$;

-- 8. ユーザー削除用の関数を作成（オプション）
CREATE OR REPLACE FUNCTION delete_user_with_cleanup(target_user_id UUID)
RETURNS void AS $$
BEGIN
    -- 関連データをクリーンアップ（必要に応じて）
    -- 注：CASCADE設定により自動的に削除されるため、通常は不要
    
    -- auth.usersから削除（関連データは自動的にカスケード削除される）
    DELETE FROM auth.users WHERE id = target_user_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 使用例：
-- SELECT delete_user_with_cleanup('user-uuid-here');