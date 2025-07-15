-- jobsテーブルを作成
CREATE TABLE IF NOT EXISTS jobs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name TEXT NOT NULL,
    job_type TEXT NOT NULL DEFAULT 'ai_matching' CHECK (job_type IN ('ai_matching', 'search', 'scrape')),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    requirement_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'ready', 'running', 'completed', 'failed')),
    priority TEXT NOT NULL DEFAULT 'normal' CHECK (priority IN ('low', 'normal', 'high')),
    parameters JSONB,
    progress INTEGER DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
    created_by UUID REFERENCES auth.users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW()),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    scheduled_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    candidate_count INTEGER DEFAULT 0
);

-- インデックスを作成
CREATE INDEX IF NOT EXISTS idx_jobs_client_id ON jobs(client_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_job_type ON jobs(job_type);
CREATE INDEX IF NOT EXISTS idx_jobs_priority ON jobs(priority);
CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_created_by ON jobs(created_by);

-- RLS (Row Level Security) を有効化
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;

-- RLSポリシーを作成
-- 管理者は全てのジョブを閲覧・操作可能
CREATE POLICY "Admin users can view all jobs" ON jobs
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM profiles
            WHERE profiles.id = auth.uid()
            AND profiles.role = 'admin'
        )
    );

CREATE POLICY "Admin users can create jobs" ON jobs
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM profiles
            WHERE profiles.id = auth.uid()
            AND profiles.role = 'admin'
        )
    );

CREATE POLICY "Admin users can update jobs" ON jobs
    FOR UPDATE USING (
        EXISTS (
            SELECT 1 FROM profiles
            WHERE profiles.id = auth.uid()
            AND profiles.role = 'admin'
        )
    );

-- マネージャーは全てのジョブを閲覧・操作可能
CREATE POLICY "Manager users can view all jobs" ON jobs
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM profiles
            WHERE profiles.id = auth.uid()
            AND profiles.role = 'manager'
        )
    );

CREATE POLICY "Manager users can create jobs" ON jobs
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM profiles
            WHERE profiles.id = auth.uid()
            AND profiles.role = 'manager'
        )
    );

CREATE POLICY "Manager users can update jobs" ON jobs
    FOR UPDATE USING (
        EXISTS (
            SELECT 1 FROM profiles
            WHERE profiles.id = auth.uid()
            AND profiles.role = 'manager'
        )
    );

-- 一般ユーザーは自分が作成したジョブのみ閲覧可能
CREATE POLICY "Users can view their own jobs" ON jobs
    FOR SELECT USING (
        created_by = auth.uid()
        OR EXISTS (
            SELECT 1 FROM profiles
            WHERE profiles.id = auth.uid()
            AND profiles.role IN ('admin', 'manager')
        )
    );

-- updated_atの自動更新用トリガー
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = TIMEZONE('utc', NOW());
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_jobs_updated_at BEFORE UPDATE
    ON jobs FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- サンプルデータ（オプション - 必要に応じてコメントアウトを解除）
-- INSERT INTO jobs (name, job_type, client_id, requirement_id, status, priority, parameters, created_by)
-- VALUES 
-- ('テストAIマッチングジョブ', 'ai_matching', 
--  (SELECT id FROM clients LIMIT 1), 
--  'req-001', 
--  'pending', 
--  'normal',
--  '{"data_source": "latest", "matching_threshold": "high", "output_sheets": true, "output_bigquery": true, "notify_completion": true}'::jsonb,
--  (SELECT id FROM auth.users LIMIT 1)
-- );