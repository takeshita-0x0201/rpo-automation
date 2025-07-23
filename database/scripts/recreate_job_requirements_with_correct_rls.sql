-- job_requirementsテーブルをUUID型で再作成するSQL（RLS修正版）
-- データが存在しないため、安全に再作成できます

-- 1. 既存のjob_requirementsテーブルを削除
DROP TABLE IF EXISTS job_requirements CASCADE;  -- CASCADEで依存する外部キーも削除

-- 2. トリガー関数の作成（存在しない場合のみ）
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 3. job_requirementsテーブルをUUID型で再作成
CREATE TABLE job_requirements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    structured_data JSONB,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID REFERENCES profiles(id),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. インデックスの作成
CREATE INDEX idx_job_requirements_client_id ON job_requirements(client_id);
CREATE INDEX idx_job_requirements_is_active ON job_requirements(is_active);
CREATE INDEX idx_job_requirements_created_at ON job_requirements(created_at DESC);

-- 5. RLSポリシーの作成
ALTER TABLE job_requirements ENABLE ROW LEVEL SECURITY;

-- 全ユーザーが閲覧可能
CREATE POLICY "Users can view job_requirements" ON job_requirements
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM profiles
            WHERE profiles.id = auth.uid()
        )
    );

-- 認証済みユーザーは作成可能
CREATE POLICY "Users can create job_requirements" ON job_requirements
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM profiles
            WHERE profiles.id = auth.uid()
        )
    );

-- 作成者本人またはadminは更新可能
CREATE POLICY "Users can update own job_requirements" ON job_requirements
    FOR UPDATE USING (
        created_by = auth.uid()
        OR EXISTS (
            SELECT 1 FROM profiles
            WHERE profiles.id = auth.uid()
            AND profiles.role = 'admin'
        )
    );

-- adminは削除可能
CREATE POLICY "Admin can delete job_requirements" ON job_requirements
    FOR DELETE USING (
        EXISTS (
            SELECT 1 FROM profiles
            WHERE profiles.id = auth.uid()
            AND profiles.role = 'admin'
        )
    );

-- 6. updated_atトリガーの作成
CREATE TRIGGER update_job_requirements_updated_at
    BEFORE UPDATE ON job_requirements
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- 7. コメントの追加
COMMENT ON TABLE job_requirements IS '採用要件マスターテーブル';
COMMENT ON COLUMN job_requirements.id IS '採用要件ID (UUID)';
COMMENT ON COLUMN job_requirements.client_id IS 'クライアントID';
COMMENT ON COLUMN job_requirements.title IS '採用要件タイトル';
COMMENT ON COLUMN job_requirements.description IS '採用要件の詳細説明';
COMMENT ON COLUMN job_requirements.structured_data IS '構造化データ（JSON形式）';
COMMENT ON COLUMN job_requirements.is_active IS '有効フラグ';

-- 8. 型の確認
SELECT 
    column_name,
    data_type,
    udt_name,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public' 
AND table_name = 'job_requirements'
ORDER BY ordinal_position;