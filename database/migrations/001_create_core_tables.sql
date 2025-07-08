-- RPO Automation コアテーブル作成
-- 実行前に UUID 拡張を有効化
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. requirements (採用要件) テーブル
CREATE TABLE requirements (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    position_name VARCHAR(255) NOT NULL,
    description TEXT,
    required_skills TEXT[], -- 必須スキル配列
    preferred_skills TEXT[], -- 歓迎スキル配列
    experience_years_min INTEGER CHECK (experience_years_min >= 0),
    experience_years_max INTEGER CHECK (experience_years_max >= experience_years_min),
    salary_min INTEGER CHECK (salary_min >= 0),
    salary_max INTEGER CHECK (salary_max >= salary_min),
    location VARCHAR(255),
    employment_type VARCHAR(50), -- 正社員、契約社員など
    headcount INTEGER DEFAULT 1 CHECK (headcount > 0),
    status VARCHAR(50) DEFAULT 'draft' CHECK (status IN ('draft', 'active', 'completed', 'cancelled')),
    created_by UUID REFERENCES profiles(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- インデックス作成
CREATE INDEX idx_requirements_client_id ON requirements(client_id);
CREATE INDEX idx_requirements_status ON requirements(status);
CREATE INDEX idx_requirements_created_at ON requirements(created_at DESC);

-- 2. candidates (候補者) テーブル
CREATE TABLE candidates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    external_id VARCHAR(255), -- 外部システム（Bizreach等）のID
    source VARCHAR(50) NOT NULL, -- データソース（bizreach, linkedin, direct等）
    email VARCHAR(255),
    phone VARCHAR(50),
    profile_data JSONB NOT NULL, -- 候補者の詳細情報をJSON形式で保存
    skills TEXT[],
    experience_years INTEGER CHECK (experience_years >= 0),
    current_position VARCHAR(255),
    current_company VARCHAR(255),
    desired_salary_min INTEGER,
    desired_salary_max INTEGER,
    location VARCHAR(255),
    job_change_urgency VARCHAR(50), -- 転職意欲（immediate, active, passive等）
    is_active BOOLEAN DEFAULT true,
    last_contacted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT unique_external_id_source UNIQUE (external_id, source)
);

-- インデックス作成
CREATE INDEX idx_candidates_source ON candidates(source);
CREATE INDEX idx_candidates_skills ON candidates USING GIN(skills);
CREATE INDEX idx_candidates_location ON candidates(location);
CREATE INDEX idx_candidates_created_at ON candidates(created_at DESC);

-- 3. search_jobs (検索ジョブ) テーブル
CREATE TABLE search_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    requirement_id UUID NOT NULL REFERENCES requirements(id) ON DELETE CASCADE,
    search_criteria JSONB NOT NULL, -- 検索条件の詳細
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
    progress INTEGER DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    total_results INTEGER DEFAULT 0,
    matched_results INTEGER DEFAULT 0,
    error_message TEXT,
    execution_time_seconds INTEGER,
    created_by UUID NOT NULL REFERENCES profiles(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- インデックス作成
CREATE INDEX idx_search_jobs_requirement_id ON search_jobs(requirement_id);
CREATE INDEX idx_search_jobs_status ON search_jobs(status);
CREATE INDEX idx_search_jobs_created_at ON search_jobs(created_at DESC);

-- 4. search_results (検索結果) テーブル
CREATE TABLE search_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    search_job_id UUID NOT NULL REFERENCES search_jobs(id) ON DELETE CASCADE,
    candidate_id UUID NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    match_score DECIMAL(5,2) CHECK (match_score >= 0 AND match_score <= 100),
    match_details JSONB, -- マッチングの詳細（どの条件にマッチしたか等）
    status VARCHAR(50) DEFAULT 'new' CHECK (status IN ('new', 'reviewed', 'shortlisted', 'contacted', 'rejected')),
    review_notes TEXT,
    reviewed_by UUID REFERENCES profiles(id),
    reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT unique_search_result UNIQUE (search_job_id, candidate_id)
);

-- インデックス作成
CREATE INDEX idx_search_results_search_job_id ON search_results(search_job_id);
CREATE INDEX idx_search_results_candidate_id ON search_results(candidate_id);
CREATE INDEX idx_search_results_match_score ON search_results(match_score DESC);
CREATE INDEX idx_search_results_status ON search_results(status);

-- 5. 更新日時を自動的に更新するトリガー関数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 各テーブルにトリガーを設定
CREATE TRIGGER update_requirements_updated_at BEFORE UPDATE ON requirements 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_candidates_updated_at BEFORE UPDATE ON candidates 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 6. Row Level Security (RLS) ポリシー
-- requirements テーブル
ALTER TABLE requirements ENABLE ROW LEVEL SECURITY;

-- 管理者は全て見られる
CREATE POLICY "Admins can view all requirements" ON requirements
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM profiles 
            WHERE profiles.id = auth.uid() 
            AND profiles.role = 'admin'
        )
    );

-- 作成者とクライアントのユーザーは自分の要件を見られる
CREATE POLICY "Users can view own requirements" ON requirements
    FOR SELECT USING (
        created_by = auth.uid() OR
        client_id IN (
            SELECT id FROM clients 
            WHERE id = requirements.client_id
        )
    );

-- candidates テーブル（認証ユーザーのみアクセス可）
ALTER TABLE candidates ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Authenticated users can view candidates" ON candidates
    FOR SELECT USING (auth.uid() IS NOT NULL);

-- search_jobs テーブル
ALTER TABLE search_jobs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own search jobs" ON search_jobs
    FOR SELECT USING (
        created_by = auth.uid() OR
        EXISTS (
            SELECT 1 FROM profiles 
            WHERE profiles.id = auth.uid() 
            AND profiles.role IN ('admin', 'manager')
        )
    );

-- search_results テーブル
ALTER TABLE search_results ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view search results" ON search_results
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM search_jobs 
            WHERE search_jobs.id = search_results.search_job_id
            AND (
                search_jobs.created_by = auth.uid() OR
                EXISTS (
                    SELECT 1 FROM profiles 
                    WHERE profiles.id = auth.uid() 
                    AND profiles.role IN ('admin', 'manager')
                )
            )
        )
    );