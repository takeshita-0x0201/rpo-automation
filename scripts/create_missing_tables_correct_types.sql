-- Supabaseで不足しているテーブルを作成するSQL（正確な型版）
-- 実行日: 2025-07-10
-- 実際の型情報に基づいて作成

-- 既存テーブルのID型：
-- candidates.id = UUID
-- clients.id = UUID
-- job_requirements.id = TEXT (gen_random_uuid()::text)
-- jobs.id = UUID
-- profiles.id = UUID
-- scraping_sessions.id = UUID
-- search_jobs.id = UUID

-- 1. client_settings（クライアント別設定）テーブル
CREATE TABLE IF NOT EXISTS client_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,  -- UUID型
    setting_key TEXT NOT NULL,
    setting_value JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(client_id, setting_key)
);

-- client_settingsのインデックス
CREATE INDEX IF NOT EXISTS idx_client_settings_client_id ON client_settings(client_id);
CREATE INDEX IF NOT EXISTS idx_client_settings_key ON client_settings(setting_key);

-- 2. ai_evaluations（AI評価結果）テーブル
CREATE TABLE IF NOT EXISTS ai_evaluations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id UUID NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,  -- UUID型
    requirement_id TEXT NOT NULL REFERENCES job_requirements(id) ON DELETE CASCADE,  -- TEXT型
    search_id TEXT,
    ai_score FLOAT CHECK (ai_score >= 0 AND ai_score <= 1),
    match_reasons TEXT[],
    concerns TEXT[],
    recommendation TEXT CHECK (recommendation IN ('high', 'medium', 'low')),
    detailed_evaluation JSONB,
    evaluated_at TIMESTAMPTZ DEFAULT NOW(),
    model_version TEXT,
    prompt_version TEXT
);

-- ai_evaluationsのインデックス
CREATE INDEX IF NOT EXISTS idx_ai_evaluations_candidate_id ON ai_evaluations(candidate_id);
CREATE INDEX IF NOT EXISTS idx_ai_evaluations_requirement_id ON ai_evaluations(requirement_id);
CREATE INDEX IF NOT EXISTS idx_ai_evaluations_search_id ON ai_evaluations(search_id);
CREATE INDEX IF NOT EXISTS idx_ai_evaluations_score ON ai_evaluations(ai_score DESC);
CREATE INDEX IF NOT EXISTS idx_ai_evaluations_recommendation ON ai_evaluations(recommendation);

-- 3. searches（検索セッション）テーブル
CREATE TABLE IF NOT EXISTS searches (
    id TEXT PRIMARY KEY,
    requirement_id TEXT NOT NULL REFERENCES job_requirements(id) ON DELETE CASCADE,  -- TEXT型
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,  -- UUID型
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    status TEXT CHECK (status IN ('running', 'completed', 'failed')),
    execution_mode TEXT CHECK (execution_mode IN ('manual', 'scheduled')),
    total_candidates INTEGER DEFAULT 0,
    evaluated_candidates INTEGER DEFAULT 0,
    matched_candidates INTEGER DEFAULT 0,
    error_message TEXT,
    search_params JSONB,
    created_by UUID REFERENCES profiles(id),  -- UUID型
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- searchesのインデックス
CREATE INDEX IF NOT EXISTS idx_searches_requirement_id ON searches(requirement_id);
CREATE INDEX IF NOT EXISTS idx_searches_client_id ON searches(client_id);
CREATE INDEX IF NOT EXISTS idx_searches_status ON searches(status);
CREATE INDEX IF NOT EXISTS idx_searches_created_by ON searches(created_by);
CREATE INDEX IF NOT EXISTS idx_searches_started_at ON searches(started_at DESC);

-- Row Level Security (RLS) ポリシー

-- client_settings RLS
ALTER TABLE client_settings ENABLE ROW LEVEL SECURITY;

-- 管理者は全て閲覧・編集可能
CREATE POLICY "Admin full access to client_settings" ON client_settings
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM profiles
            WHERE profiles.id = auth.uid()
            AND profiles.role = 'admin'
        )
    );

-- 一般ユーザーは閲覧のみ可能
CREATE POLICY "User read access to client_settings" ON client_settings
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM profiles
            WHERE profiles.id = auth.uid()
            AND profiles.role = 'user'
        )
    );

-- ai_evaluations RLS
ALTER TABLE ai_evaluations ENABLE ROW LEVEL SECURITY;

-- 全スタッフが閲覧可能
CREATE POLICY "Staff read access to ai_evaluations" ON ai_evaluations
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM profiles
            WHERE profiles.id = auth.uid()
        )
    );

-- 管理者のみ編集可能
CREATE POLICY "Admin write access to ai_evaluations" ON ai_evaluations
    FOR INSERT USING (
        EXISTS (
            SELECT 1 FROM profiles
            WHERE profiles.id = auth.uid()
            AND profiles.role = 'admin'
        )
    );

CREATE POLICY "Admin update access to ai_evaluations" ON ai_evaluations
    FOR UPDATE USING (
        EXISTS (
            SELECT 1 FROM profiles
            WHERE profiles.id = auth.uid()
            AND profiles.role = 'admin'
        )
    );

-- searches RLS
ALTER TABLE searches ENABLE ROW LEVEL SECURITY;

-- 本人のジョブのみ閲覧可能、adminは全て閲覧可能
CREATE POLICY "User own searches access" ON searches
    FOR SELECT USING (
        auth.uid() = created_by
        OR EXISTS (
            SELECT 1 FROM profiles
            WHERE profiles.id = auth.uid()
            AND profiles.role = 'admin'
        )
    );

-- 認証済みユーザーは作成可能
CREATE POLICY "Authenticated users can create searches" ON searches
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM profiles
            WHERE profiles.id = auth.uid()
        )
    );

-- 本人またはadminは更新可能
CREATE POLICY "User can update own searches" ON searches
    FOR UPDATE USING (
        auth.uid() = created_by
        OR EXISTS (
            SELECT 1 FROM profiles
            WHERE profiles.id = auth.uid()
            AND profiles.role = 'admin'
        )
    );

-- トリガー関数: updated_atを自動更新
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- client_settingsのupdated_atトリガー
DO $$
BEGIN
    CREATE TRIGGER update_client_settings_updated_at
        BEFORE UPDATE ON client_settings
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at();
EXCEPTION
    WHEN duplicate_object THEN
        NULL;  -- トリガーが既に存在する場合は何もしない
END$$;

-- コメント追加
COMMENT ON TABLE client_settings IS 'クライアント別の設定を管理するテーブル';
COMMENT ON TABLE ai_evaluations IS 'AIによる候補者評価結果を保存するテーブル';
COMMENT ON TABLE searches IS '検索セッション情報を管理するテーブル';

-- 確認用：作成されたテーブルの型を確認
/*
SELECT 
    table_name,
    column_name,
    data_type,
    udt_name
FROM information_schema.columns
WHERE table_schema = 'public' 
AND table_name IN ('client_settings', 'ai_evaluations', 'searches')
AND column_name LIKE '%_id'
ORDER BY table_name, column_name;
*/