-- RPO Automation System - 不足している3つのテーブルを作成
-- 実行前の確認: profiles, clients, search_jobs テーブルが既に存在していること

-- 1. requirements（採用要件）テーブルの作成
CREATE TABLE IF NOT EXISTS requirements (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    position_name VARCHAR(255) NOT NULL,
    description TEXT,
    required_skills TEXT[],
    preferred_skills TEXT[],
    experience_years_min INTEGER CHECK (experience_years_min >= 0),
    experience_years_max INTEGER CHECK (experience_years_max >= experience_years_min OR experience_years_max IS NULL),
    salary_min INTEGER CHECK (salary_min >= 0),
    salary_max INTEGER CHECK (salary_max >= salary_min OR salary_max IS NULL),
    location VARCHAR(255),
    employment_type VARCHAR(50) DEFAULT '正社員',
    headcount INTEGER DEFAULT 1 CHECK (headcount > 0),
    status VARCHAR(50) DEFAULT 'draft' CHECK (status IN ('draft', 'active', 'completed', 'cancelled')),
    created_by UUID REFERENCES profiles(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- requirementsテーブルのインデックス
CREATE INDEX IF NOT EXISTS idx_requirements_client_id ON requirements(client_id);
CREATE INDEX IF NOT EXISTS idx_requirements_status ON requirements(status);
CREATE INDEX IF NOT EXISTS idx_requirements_created_at ON requirements(created_at DESC);

-- requirementsテーブルのコメント
COMMENT ON TABLE requirements IS '採用要件テーブル';
COMMENT ON COLUMN requirements.id IS '採用要件ID（search_jobs.requirement_idと連携）';
COMMENT ON COLUMN requirements.required_skills IS '必須スキルの配列';
COMMENT ON COLUMN requirements.preferred_skills IS '歓迎スキルの配列';

-- 2. candidates（候補者）テーブルの作成
CREATE TABLE IF NOT EXISTS candidates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id VARCHAR(255),
    source VARCHAR(50) NOT NULL DEFAULT 'manual',
    email VARCHAR(255),
    phone VARCHAR(50),
    profile_data JSONB NOT NULL DEFAULT '{}',
    skills TEXT[],
    experience_years INTEGER CHECK (experience_years >= 0),
    current_position VARCHAR(255),
    current_company VARCHAR(255),
    desired_salary_min INTEGER,
    desired_salary_max INTEGER,
    location VARCHAR(255),
    job_change_urgency VARCHAR(50),
    is_active BOOLEAN DEFAULT true,
    last_contacted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT unique_external_id_source UNIQUE (external_id, source)
);

-- candidatesテーブルのインデックス
CREATE INDEX IF NOT EXISTS idx_candidates_source ON candidates(source);
CREATE INDEX IF NOT EXISTS idx_candidates_skills ON candidates USING GIN(skills);
CREATE INDEX IF NOT EXISTS idx_candidates_location ON candidates(location);
CREATE INDEX IF NOT EXISTS idx_candidates_created_at ON candidates(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_candidates_email ON candidates(email);

-- candidatesテーブルのコメント
COMMENT ON TABLE candidates IS '候補者マスタテーブル';
COMMENT ON COLUMN candidates.external_id IS '外部システム（Bizreach等）での候補者ID';
COMMENT ON COLUMN candidates.source IS 'データソース（bizreach, linkedin, manual等）';
COMMENT ON COLUMN candidates.profile_data IS '候補者の詳細プロフィール（JSON形式）';

-- 3. search_results（検索結果）テーブルの作成
CREATE TABLE IF NOT EXISTS search_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    search_job_id UUID NOT NULL REFERENCES search_jobs(id) ON DELETE CASCADE,
    candidate_id UUID NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    match_score DECIMAL(5,2) DEFAULT 0 CHECK (match_score >= 0 AND match_score <= 100),
    match_details JSONB DEFAULT '{}',
    status VARCHAR(50) DEFAULT 'new' CHECK (status IN ('new', 'reviewed', 'shortlisted', 'contacted', 'rejected')),
    review_notes TEXT,
    reviewed_by UUID REFERENCES profiles(id),
    reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT unique_search_result UNIQUE (search_job_id, candidate_id)
);

-- search_resultsテーブルのインデックス
CREATE INDEX IF NOT EXISTS idx_search_results_search_job_id ON search_results(search_job_id);
CREATE INDEX IF NOT EXISTS idx_search_results_candidate_id ON search_results(candidate_id);
CREATE INDEX IF NOT EXISTS idx_search_results_match_score ON search_results(match_score DESC);
CREATE INDEX IF NOT EXISTS idx_search_results_status ON search_results(status);

-- search_resultsテーブルのコメント
COMMENT ON TABLE search_results IS '検索結果（ジョブと候補者のマッチング）';
COMMENT ON COLUMN search_results.match_score IS 'マッチングスコア（0-100）';
COMMENT ON COLUMN search_results.match_details IS 'マッチングの詳細（どの条件にマッチしたか等）';

-- 4. 更新日時を自動的に更新するトリガー関数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 各テーブルにトリガーを設定
DROP TRIGGER IF EXISTS update_requirements_updated_at ON requirements;
CREATE TRIGGER update_requirements_updated_at 
    BEFORE UPDATE ON requirements 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_candidates_updated_at ON candidates;
CREATE TRIGGER update_candidates_updated_at 
    BEFORE UPDATE ON candidates 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 5. Row Level Security (RLS) の設定
-- requirements
ALTER TABLE requirements ENABLE ROW LEVEL SECURITY;

-- 認証されたユーザーは全ての要件を閲覧可能
DROP POLICY IF EXISTS "requirements_select_policy" ON requirements;
CREATE POLICY "requirements_select_policy" ON requirements
    FOR SELECT
    USING (auth.uid() IS NOT NULL);

-- adminとmanagerは全ての操作が可能
DROP POLICY IF EXISTS "requirements_all_policy" ON requirements;
CREATE POLICY "requirements_all_policy" ON requirements
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM profiles 
            WHERE profiles.id = auth.uid() 
            AND profiles.role IN ('admin', 'manager')
        )
    );

-- candidates
ALTER TABLE candidates ENABLE ROW LEVEL SECURITY;

-- 認証されたユーザーは全ての候補者を閲覧可能
DROP POLICY IF EXISTS "candidates_select_policy" ON candidates;
CREATE POLICY "candidates_select_policy" ON candidates
    FOR SELECT
    USING (auth.uid() IS NOT NULL);

-- adminとmanagerは全ての操作が可能
DROP POLICY IF EXISTS "candidates_all_policy" ON candidates;
CREATE POLICY "candidates_all_policy" ON candidates
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM profiles 
            WHERE profiles.id = auth.uid() 
            AND profiles.role IN ('admin', 'manager')
        )
    );

-- search_results
ALTER TABLE search_results ENABLE ROW LEVEL SECURITY;

-- 認証されたユーザーは全ての検索結果を閲覧可能
DROP POLICY IF EXISTS "search_results_select_policy" ON search_results;
CREATE POLICY "search_results_select_policy" ON search_results
    FOR SELECT
    USING (auth.uid() IS NOT NULL);

-- adminとmanagerは全ての操作が可能
DROP POLICY IF EXISTS "search_results_all_policy" ON search_results;
CREATE POLICY "search_results_all_policy" ON search_results
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM profiles 
            WHERE profiles.id = auth.uid() 
            AND profiles.role IN ('admin', 'manager')
        )
    );

-- 6. 作成確認
SELECT 
    table_name,
    CASE 
        WHEN table_name IS NOT NULL THEN '✅ 作成成功'
        ELSE '❌ 作成失敗'
    END AS status
FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN ('requirements', 'candidates', 'search_results')
ORDER BY table_name;

-- 7. サンプルデータ投入（オプション - 必要に応じてコメントを外して実行）
/*
-- テスト用の採用要件
INSERT INTO requirements (
    client_id,
    position_name,
    description,
    required_skills,
    preferred_skills,
    experience_years_min,
    experience_years_max,
    salary_min,
    salary_max,
    location,
    employment_type,
    status,
    created_by
) VALUES (
    (SELECT id FROM clients LIMIT 1),
    'フルスタックエンジニア',
    'Webアプリケーションの設計から実装まで幅広く担当していただきます。',
    ARRAY['JavaScript', 'React', 'Node.js', 'PostgreSQL'],
    ARRAY['TypeScript', 'Next.js', 'AWS', 'Docker'],
    3,
    8,
    6000000,
    10000000,
    '東京都',
    '正社員',
    'active',
    (SELECT id FROM profiles WHERE role = 'admin' LIMIT 1)
);

-- テスト用の候補者
INSERT INTO candidates (
    external_id,
    source,
    email,
    profile_data,
    skills,
    experience_years,
    current_position,
    current_company,
    location
) VALUES (
    'TEST_001',
    'manual',
    'test.candidate@example.com',
    '{"summary": "5年以上のWeb開発経験を持つエンジニア", "strengths": ["フロントエンド開発", "UI/UX設計"]}',
    ARRAY['JavaScript', 'React', 'Vue.js', 'Node.js', 'PostgreSQL'],
    5,
    'シニアエンジニア',
    'テスト株式会社',
    '東京都'
);
*/