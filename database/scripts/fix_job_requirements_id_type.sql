-- job_requirements.idをTEXT型からUUID型に変更するSQL
-- 注意: このスクリプトは既存のデータと外部キー制約に影響を与える可能性があります

-- 1. まず現在の状況を確認
SELECT COUNT(*) as record_count FROM job_requirements;

-- 2. 外部キー制約の確認
SELECT 
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
AND ccu.table_name = 'job_requirements';

-- 3. バックアップテーブルの作成
CREATE TABLE job_requirements_backup AS SELECT * FROM job_requirements;

-- 4. 外部キー制約の削除（必要に応じて）
-- ここに外部キー制約の削除コマンドを追加

-- 5. 新しいテーブルの作成（UUID型で）
CREATE TABLE job_requirements_new (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    structured_data JSONB,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID REFERENCES profiles(id),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    job_requirements_id TEXT -- 旧ID保持用
);

-- 6. データの移行（TEXT型のUUID文字列をUUID型に変換）
INSERT INTO job_requirements_new (
    id,
    client_id,
    title,
    description,
    structured_data,
    is_active,
    created_at,
    created_by,
    updated_at,
    job_requirements_id
)
SELECT 
    id::uuid,  -- TEXT型のUUID文字列をUUID型に変換
    client_id,
    title,
    description,
    structured_data,
    is_active,
    created_at,
    created_by,
    updated_at,
    job_requirements_id
FROM job_requirements;

-- 7. テーブルの入れ替え
ALTER TABLE job_requirements RENAME TO job_requirements_old;
ALTER TABLE job_requirements_new RENAME TO job_requirements;

-- 8. インデックスの再作成
CREATE INDEX idx_job_requirements_client_id ON job_requirements(client_id);
CREATE INDEX idx_job_requirements_is_active ON job_requirements(is_active);
CREATE INDEX idx_job_requirements_created_at ON job_requirements(created_at DESC);

-- 9. RLSポリシーの再作成（必要に応じて）
-- 既存のRLSポリシーをここに追加

-- 10. 確認
SELECT 
    column_name,
    data_type,
    udt_name
FROM information_schema.columns
WHERE table_schema = 'public' 
AND table_name = 'job_requirements'
AND column_name = 'id';

-- 11. 古いテーブルの削除（確認後）
-- DROP TABLE job_requirements_old;
-- DROP TABLE job_requirements_backup;