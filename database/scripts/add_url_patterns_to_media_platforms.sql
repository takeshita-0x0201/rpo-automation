-- media_platformsテーブルにurl_patternsカラムを追加
ALTER TABLE media_platforms 
ADD COLUMN IF NOT EXISTS url_patterns JSONB DEFAULT '[]'::jsonb;

-- コメントを追加
COMMENT ON COLUMN media_platforms.url_patterns IS 'URLパターンの配列。各媒体のドメインやURLパターンを格納';

-- 既存レコードのURL パターンを更新
UPDATE media_platforms SET url_patterns = 
CASE 
    WHEN name = 'bizreach' THEN '["cr-support.jp", "bizreach.jp"]'::jsonb
    WHEN name = 'linkedin' THEN '["linkedin.com"]'::jsonb
    WHEN name = 'green' THEN '["green-japan.com"]'::jsonb
    WHEN name = 'wantedly' THEN '["wantedly.com"]'::jsonb
    WHEN name = 'doda' THEN '["doda.jp"]'::jsonb
    WHEN name = 'recruit_agent' THEN '["r-agent.com"]'::jsonb
    WHEN name = 'indeed' THEN '["indeed.com", "jp.indeed.com"]'::jsonb
    ELSE '[]'::jsonb
END
WHERE url_patterns = '[]'::jsonb OR url_patterns IS NULL;