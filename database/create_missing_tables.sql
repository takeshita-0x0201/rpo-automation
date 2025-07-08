-- RPO Automation System - 不足テーブル作成SQL
-- 前提: search_jobsテーブルが既に存在する

-- 1. requirements（採用要件）テーブル
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
    employment_type VARCHAR(50),
    headcount INTEGER DEFAULT 1 CHECK (headcount > 0),
    status VARCHAR(50) DEFAULT 'draft' CHECK (status IN ('draft', 'active', 'completed', 'cancelled')),
    created_by UUID REFERENCES profiles(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- requirementsのインデックス
CREATE INDEX IF NOT EXISTS idx_requirements_client_id ON requirements(client_id);
CREATE INDEX IF NOT EXISTS idx_requirements_status ON requirements(status);
CREATE INDEX IF NOT EXISTS idx_requirements_created_at ON requirements(created_at DESC);

-- 2. candidates（候補者）テーブル
CREATE TABLE IF NOT EXISTS candidates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id VARCHAR(255),
    source VARCHAR(50) NOT NULL,
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

-- candidatesのインデックス
CREATE INDEX IF NOT EXISTS idx_candidates_source ON candidates(source);
CREATE INDEX IF NOT EXISTS idx_candidates_skills ON candidates USING GIN(skills);
CREATE INDEX IF NOT EXISTS idx_candidates_location ON candidates(location);
CREATE INDEX IF NOT EXISTS idx_candidates_created_at ON candidates(created_at DESC);

-- 3. search_results（検索結果）テーブル
CREATE TABLE IF NOT EXISTS search_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    search_job_id UUID NOT NULL REFERENCES search_jobs(id) ON DELETE CASCADE,
    candidate_id UUID NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    match_score DECIMAL(5,2) CHECK (match_score >= 0 AND match_score <= 100),
    match_details JSONB DEFAULT '{}',
    status VARCHAR(50) DEFAULT 'new' CHECK (status IN ('new', 'reviewed', 'shortlisted', 'contacted', 'rejected')),
    review_notes TEXT,
    reviewed_by UUID REFERENCES profiles(id),
    reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT unique_search_result UNIQUE (search_job_id, candidate_id)
);

-- search_resultsのインデックス
CREATE INDEX IF NOT EXISTS idx_search_results_search_job_id ON search_results(search_job_id);
CREATE INDEX IF NOT EXISTS idx_search_results_candidate_id ON search_results(candidate_id);
CREATE INDEX IF NOT EXISTS idx_search_results_match_score ON search_results(match_score DESC);
CREATE INDEX IF NOT EXISTS idx_search_results_status ON search_results(status);

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

-- 5. RLS (Row Level Security) の設定
-- requirements
ALTER TABLE requirements ENABLE ROW LEVEL SECURITY;

-- 全ユーザーが要件を閲覧可能（認証必須）
CREATE POLICY "Authenticated users can view requirements" ON requirements
    FOR SELECT USING (auth.uid() IS NOT NULL);

-- adminとmanagerは全ての操作が可能
CREATE POLICY "Admins and managers can manage requirements" ON requirements
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM profiles 
            WHERE profiles.id = auth.uid() 
            AND profiles.role IN ('admin', 'manager')
        )
    );

-- candidates
ALTER TABLE candidates ENABLE ROW LEVEL SECURITY;

-- 認証ユーザーは候補者を閲覧可能
CREATE POLICY "Authenticated users can view candidates" ON candidates
    FOR SELECT USING (auth.uid() IS NOT NULL);

-- adminとmanagerは全ての操作が可能
CREATE POLICY "Admins and managers can manage candidates" ON candidates
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM profiles 
            WHERE profiles.id = auth.uid() 
            AND profiles.role IN ('admin', 'manager')
        )
    );

-- search_results
ALTER TABLE search_results ENABLE ROW LEVEL SECURITY;

-- 認証ユーザーは検索結果を閲覧可能
CREATE POLICY "Authenticated users can view search results" ON search_results
    FOR SELECT USING (auth.uid() IS NOT NULL);

-- adminとmanagerは全ての操作が可能
CREATE POLICY "Admins and managers can manage search results" ON search_results
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM profiles 
            WHERE profiles.id = auth.uid() 
            AND profiles.role IN ('admin', 'manager')
        )
    );

-- 6. サンプルデータ（オプション - コメントアウトを外して使用）
/*
-- サンプル採用要件
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
    status
) VALUES (
    (SELECT id FROM clients LIMIT 1),
    'シニアバックエンドエンジニア',
    'マイクロサービスアーキテクチャの設計・開発をリードしていただきます。',
    ARRAY['Python', 'Django', 'PostgreSQL', 'Docker'],
    ARRAY['Kubernetes', 'AWS', 'GraphQL'],
    5,
    10,
    8000000,
    12000000,
    '東京都',
    'active'
);
*/