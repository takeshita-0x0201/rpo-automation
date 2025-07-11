-- Supabaseで不足しているテーブルを作成するSQL（RLS修正版）
-- 実行日: 2025-07-10
-- job_requirementsテーブルをUUID型に変更後に実行してください

-- トリガー関数の作成（存在しない場合のみ）
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 1. client_settings（クライアント別設定）テーブル
CREATE TABLE IF NOT EXISTS client_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
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
    candidate_id UUID NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    requirement_id UUID NOT NULL REFERENCES job_requirements(id) ON DELETE CASCADE,
    search_id TEXT,  -- 検索IDは文字列のまま
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
    id TEXT PRIMARY KEY,  -- 検索IDは文字列型を維持（セッションIDなど）
    requirement_id UUID NOT NULL REFERENCES job_requirements(id) ON DELETE CASCADE,
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    status TEXT CHECK (status IN ('running', 'completed', 'failed')),
    execution_mode TEXT CHECK (execution_mode IN ('manual', 'scheduled')),
    total_candidates INTEGER DEFAULT 0,
    evaluated_candidates INTEGER DEFAULT 0,
    matched_candidates INTEGER DEFAULT 0,
    error_message TEXT,
    search_params JSONB,
    created_by UUID REFERENCES profiles(id),
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

-- 閲覧ポリシー
CREATE POLICY "Users can view client_settings" ON client_settings
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM profiles
            WHERE profiles.id = auth.uid()
        )
    );

-- 作成ポリシー（adminのみ）
CREATE POLICY "Admin can create client_settings" ON client_settings
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM profiles
            WHERE profiles.id = auth.uid()
            AND profiles.role = 'admin'
        )
    );

-- 更新ポリシー（adminのみ）
CREATE POLICY "Admin can update client_settings" ON client_settings
    FOR UPDATE USING (
        EXISTS (
            SELECT 1 FROM profiles
            WHERE profiles.id = auth.uid()
            AND profiles.role = 'admin'
        )
    );

-- 削除ポリシー（adminのみ）
CREATE POLICY "Admin can delete client_settings" ON client_settings
    FOR DELETE USING (
        EXISTS (
            SELECT 1 FROM profiles
            WHERE profiles.id = auth.uid()
            AND profiles.role = 'admin'
        )
    );

-- ai_evaluations RLS
ALTER TABLE ai_evaluations ENABLE ROW LEVEL SECURITY;

-- 全スタッフが閲覧可能
CREATE POLICY "Staff can view ai_evaluations" ON ai_evaluations
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM profiles
            WHERE profiles.id = auth.uid()
        )
    );

-- 管理者のみ作成可能
CREATE POLICY "Admin can create ai_evaluations" ON ai_evaluations
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM profiles
            WHERE profiles.id = auth.uid()
            AND profiles.role = 'admin'
        )
    );

-- 管理者のみ更新可能
CREATE POLICY "Admin can update ai_evaluations" ON ai_evaluations
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
CREATE POLICY "User can view own searches" ON searches
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

-- トリガーの作成
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

-- 作成後の確認クエリ
SELECT 
    table_name,
    column_name,
    data_type,
    udt_name
FROM information_schema.columns
WHERE table_schema = 'public' 
AND table_name IN ('client_settings', 'ai_evaluations', 'searches', 'job_requirements')
AND column_name IN ('id', 'client_id', 'candidate_id', 'requirement_id', 'created_by')
ORDER BY table_name, column_name;