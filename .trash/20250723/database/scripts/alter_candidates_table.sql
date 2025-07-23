-- candidatesテーブルの構造を変更するSQL
-- 既存のid、created_at、updated_atは維持

-- 1. 新しいカラムを追加（存在しない場合）
ALTER TABLE candidates 
ADD COLUMN IF NOT EXISTS candidate_id TEXT,
ADD COLUMN IF NOT EXISTS candidate_link TEXT,
ADD COLUMN IF NOT EXISTS candidate_company TEXT,
ADD COLUMN IF NOT EXISTS candidate_resume TEXT;

-- 2. 既存データがある場合の移行（オプション）
-- bizreach_urlからcandidate_idを抽出
UPDATE candidates 
SET 
    candidate_id = CASE 
        WHEN bizreach_url LIKE '%candidate=%' THEN 
            substring(bizreach_url from 'candidate=([0-9]+)')
        WHEN bizreach_id IS NOT NULL THEN 
            bizreach_id
        ELSE NULL
    END,
    candidate_link = COALESCE(bizreach_url, profile_url),
    candidate_company = current_company
WHERE candidate_id IS NULL;

-- 3. 新しいカラムにNOT NULL制約を追加（データ移行後）
-- 注意: 既存データがある場合は、まず上記のUPDATEを実行してから
ALTER TABLE candidates 
ALTER COLUMN candidate_id SET NOT NULL,
ALTER COLUMN candidate_link SET NOT NULL;

-- 4. リレーションカラムの追加（存在しない場合）
ALTER TABLE candidates 
ADD COLUMN IF NOT EXISTS scraping_session_id UUID REFERENCES scraping_sessions(id),
ADD COLUMN IF NOT EXISTS client_id UUID REFERENCES clients(id),
ADD COLUMN IF NOT EXISTS requirement_id UUID REFERENCES job_requirements(id);

-- 5. scraped_dataから値を移行（既存データがある場合）
UPDATE candidates 
SET 
    client_id = CASE 
        WHEN scraped_data ? 'client_id' THEN (scraped_data->>'client_id')::uuid 
        ELSE NULL 
    END,
    requirement_id = CASE 
        WHEN scraped_data ? 'requirement_id' THEN (scraped_data->>'requirement_id')::uuid 
        ELSE NULL 
    END
WHERE client_id IS NULL AND scraped_data IS NOT NULL;

-- 6. 重複防止の制約を追加
ALTER TABLE candidates 
ADD CONSTRAINT IF NOT EXISTS unique_candidate_per_platform 
UNIQUE (candidate_id, platform);

-- 7. インデックスの作成
CREATE INDEX IF NOT EXISTS idx_candidates_candidate_id ON candidates(candidate_id);
CREATE INDEX IF NOT EXISTS idx_candidates_company ON candidates(candidate_company);
CREATE INDEX IF NOT EXISTS idx_candidates_client ON candidates(client_id);
CREATE INDEX IF NOT EXISTS idx_candidates_requirement ON candidates(requirement_id);
CREATE INDEX IF NOT EXISTS idx_candidates_session ON candidates(scraping_session_id);

-- 8. 不要なカラムの確認（削除は手動で判断）
-- 以下のカラムは新しい構造では不要になる可能性があります：
-- - name
-- - bizreach_id (candidate_idに統合)
-- - bizreach_url (candidate_linkに統合)
-- - current_company (candidate_companyに統合)
-- - current_position
-- - current_title
-- - skills
-- - education
-- - experience_years
-- - profile_url
-- - profile_summary
-- - scraped_data (正規化カラムに移行後)

-- 確認クエリ
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public' 
AND table_name = 'candidates'
ORDER BY ordinal_position;