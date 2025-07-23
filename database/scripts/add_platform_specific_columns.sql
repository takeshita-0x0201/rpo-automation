-- 新しいプラットフォーム用のカラムを追加（必要に応じて）

-- 例：特定のサイト固有の情報を保存する場合
ALTER TABLE candidates
ADD COLUMN IF NOT EXISTS example_site_data JSONB;

-- platformカラムに新しい値を許可（enumの場合）
-- 注：既存のplatformカラムがTEXT型の場合は不要

-- インデックスの追加（パフォーマンス向上）
CREATE INDEX IF NOT EXISTS idx_candidates_platform_example 
ON candidates(platform) 
WHERE platform = 'example-site';