-- candidatesテーブルの最終的な構造変更SQL
-- 維持するカラム: id, created_at, updated_at, platform

-- 1. platformカラムの確認と追加（存在しない場合）
ALTER TABLE candidates 
ADD COLUMN IF NOT EXISTS platform TEXT DEFAULT 'bizreach';

-- 2. スクレイピング関連の新しいカラムを追加
ALTER TABLE candidates 
ADD COLUMN IF NOT EXISTS candidate_id TEXT,
ADD COLUMN IF NOT EXISTS candidate_link TEXT,
ADD COLUMN IF NOT EXISTS candidate_company TEXT,
ADD COLUMN IF NOT EXISTS candidate_resume TEXT;

-- 3. リレーション用カラムの追加
ALTER TABLE candidates 
ADD COLUMN IF NOT EXISTS scraping_session_id UUID REFERENCES scraping_sessions(id),
ADD COLUMN IF NOT EXISTS client_id UUID REFERENCES clients(id),
ADD COLUMN IF NOT EXISTS requirement_id UUID REFERENCES job_requirements(id);

-- 4. メタデータカラムの追加（存在しない場合）
ALTER TABLE candidates 
ADD COLUMN IF NOT EXISTS scraped_at TIMESTAMPTZ DEFAULT NOW(),
ADD COLUMN IF NOT EXISTS scraped_by UUID REFERENCES profiles(id);

-- 5. 既存データの移行（データが存在する場合）
UPDATE candidates 
SET 
    -- candidate_idの設定
    candidate_id = CASE 
        WHEN bizreach_url LIKE '%candidate=%' THEN 
            substring(bizreach_url from 'candidate=([0-9]+)')
        WHEN bizreach_id IS NOT NULL THEN 
            bizreach_id
        ELSE NULL
    END,
    -- candidate_linkの設定
    candidate_link = COALESCE(bizreach_url, profile_url),
    -- candidate_companyの設定
    candidate_company = current_company,
    -- platformの確認（デフォルトがbizreachでない場合）
    platform = COALESCE(platform, 'bizreach')
WHERE candidate_id IS NULL;

-- 6. scraped_dataからリレーションデータを移行
UPDATE candidates 
SET 
    client_id = CASE 
        WHEN scraped_data ? 'client_id' AND scraped_data->>'client_id' != 'null' THEN 
            (scraped_data->>'client_id')::uuid 
        ELSE NULL 
    END,
    requirement_id = CASE 
        WHEN scraped_data ? 'requirement_id' AND scraped_data->>'requirement_id' != 'null' THEN 
            (scraped_data->>'requirement_id')::uuid 
        ELSE NULL 
    END
WHERE client_id IS NULL AND scraped_data IS NOT NULL;

-- 7. session_idからscraping_session_idへの移行
UPDATE candidates 
SET scraping_session_id = session_id::uuid
WHERE scraping_session_id IS NULL 
AND session_id IS NOT NULL 
AND session_id ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$';

-- 8. NOT NULL制約の追加（データ移行後）
ALTER TABLE candidates 
ALTER COLUMN candidate_id SET NOT NULL,
ALTER COLUMN candidate_link SET NOT NULL,
ALTER COLUMN platform SET NOT NULL;

-- 9. 重複防止の制約を追加
ALTER TABLE candidates 
DROP CONSTRAINT IF EXISTS unique_candidate_per_platform;
ALTER TABLE candidates 
ADD CONSTRAINT unique_candidate_per_platform 
UNIQUE (candidate_id, platform);

-- 10. インデックスの作成
CREATE INDEX IF NOT EXISTS idx_candidates_candidate_id ON candidates(candidate_id);
CREATE INDEX IF NOT EXISTS idx_candidates_platform ON candidates(platform);
CREATE INDEX IF NOT EXISTS idx_candidates_company ON candidates(candidate_company);
CREATE INDEX IF NOT EXISTS idx_candidates_client ON candidates(client_id);
CREATE INDEX IF NOT EXISTS idx_candidates_requirement ON candidates(requirement_id);
CREATE INDEX IF NOT EXISTS idx_candidates_session ON candidates(scraping_session_id);
CREATE INDEX IF NOT EXISTS idx_candidates_scraped_at ON candidates(scraped_at DESC);

-- 11. 最終的なテーブル構造の確認
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default,
    CASE 
        WHEN column_name IN ('id', 'created_at', 'updated_at', 'platform', 
                            'candidate_id', 'candidate_link', 'candidate_company', 
                            'candidate_resume', 'scraped_at', 'scraped_by',
                            'client_id', 'requirement_id', 'scraping_session_id') 
        THEN '✓ 必要' 
        ELSE '× 削除候補' 
    END as status
FROM information_schema.columns
WHERE table_schema = 'public' 
AND table_name = 'candidates'
ORDER BY 
    CASE 
        WHEN column_name IN ('id', 'candidate_id', 'candidate_link', 
                            'candidate_company', 'candidate_resume') THEN 1
        WHEN column_name IN ('platform', 'scraped_at', 'scraped_by') THEN 2
        WHEN column_name IN ('client_id', 'requirement_id', 'scraping_session_id') THEN 3
        WHEN column_name IN ('created_at', 'updated_at') THEN 4
        ELSE 5
    END,
    column_name;

-- 12. 削除候補のカラム一覧（手動で確認後に削除）
-- これらのカラムは新しい構造では不要になります：
/*
ALTER TABLE candidates 
DROP COLUMN IF EXISTS name,
DROP COLUMN IF EXISTS email,
DROP COLUMN IF EXISTS phone,
DROP COLUMN IF EXISTS bizreach_id,
DROP COLUMN IF EXISTS bizreach_url,
DROP COLUMN IF EXISTS current_title,
DROP COLUMN IF EXISTS current_position,
DROP COLUMN IF EXISTS current_company,
DROP COLUMN IF EXISTS experience_years,
DROP COLUMN IF EXISTS skills,
DROP COLUMN IF EXISTS education,
DROP COLUMN IF EXISTS profile_url,
DROP COLUMN IF EXISTS profile_summary,
DROP COLUMN IF EXISTS search_id,
DROP COLUMN IF EXISTS session_id,
DROP COLUMN IF EXISTS scraped_data,
DROP COLUMN IF EXISTS external_id,
DROP COLUMN IF EXISTS source,
DROP COLUMN IF EXISTS profile_data,
DROP COLUMN IF EXISTS desired_salary_min,
DROP COLUMN IF EXISTS desired_salary_max,
DROP COLUMN IF EXISTS location,
DROP COLUMN IF EXISTS job_change_urgency,
DROP COLUMN IF EXISTS is_active,
DROP COLUMN IF EXISTS last_contacted_at;
*/