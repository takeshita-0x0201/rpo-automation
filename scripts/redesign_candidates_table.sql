-- candidatesテーブルの再設計SQL
-- スクレイピングデータに直接関わる最小限のカラム構成

-- 1. 既存のcandidatesテーブルをバックアップ
CREATE TABLE candidates_backup AS SELECT * FROM candidates;

-- 2. 既存のcandidatesテーブルを削除（外部キー制約も含めて）
DROP TABLE IF EXISTS candidates CASCADE;

-- 3. 新しいcandidatesテーブルを作成
CREATE TABLE candidates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- スクレイピングデータ直接関連カラム
    candidate_id TEXT NOT NULL,           -- Bizreach等のプラットフォーム上の候補者ID
    candidate_link TEXT NOT NULL,         -- 候補者プロフィールへのリンク
    candidate_company TEXT,               -- 現在の所属企業
    candidate_resume TEXT,                -- レジュメ/プロフィール情報（テキストまたはURL）
    
    -- メタデータ
    platform TEXT DEFAULT 'bizreach',     -- スクレイピング元プラットフォーム
    scraped_at TIMESTAMPTZ DEFAULT NOW(), -- スクレイピング日時
    scraped_by UUID REFERENCES profiles(id), -- スクレイピング実行者
    
    -- リレーション
    scraping_session_id UUID REFERENCES scraping_sessions(id), -- スクレイピングセッション
    client_id UUID REFERENCES clients(id),                     -- クライアント
    requirement_id UUID REFERENCES job_requirements(id),       -- 採用要件
    
    -- タイムスタンプ
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- 重複防止の制約
    CONSTRAINT unique_candidate_per_platform UNIQUE (candidate_id, platform)
);

-- 4. インデックスの作成
CREATE INDEX idx_candidates_candidate_id ON candidates(candidate_id);
CREATE INDEX idx_candidates_platform ON candidates(platform);
CREATE INDEX idx_candidates_company ON candidates(candidate_company);
CREATE INDEX idx_candidates_session ON candidates(scraping_session_id);
CREATE INDEX idx_candidates_client ON candidates(client_id);
CREATE INDEX idx_candidates_requirement ON candidates(requirement_id);
CREATE INDEX idx_candidates_scraped_at ON candidates(scraped_at DESC);

-- 5. updated_atトリガーの作成
CREATE TRIGGER update_candidates_updated_at
    BEFORE UPDATE ON candidates
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- 6. コメントの追加
COMMENT ON TABLE candidates IS 'スクレイピングした候補者データを格納するテーブル';
COMMENT ON COLUMN candidates.candidate_id IS 'プラットフォーム上の候補者ID（例：Bizreach ID）';
COMMENT ON COLUMN candidates.candidate_link IS '候補者プロフィールページへのURL';
COMMENT ON COLUMN candidates.candidate_company IS '候補者の現在の所属企業名';
COMMENT ON COLUMN candidates.candidate_resume IS 'レジュメ情報（テキストまたはPDF URL）';

-- 7. RLSポリシーの設定
ALTER TABLE candidates ENABLE ROW LEVEL SECURITY;

-- 閲覧ポリシー：全スタッフが閲覧可能
CREATE POLICY "Staff can view candidates" ON candidates
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM profiles
            WHERE profiles.id = auth.uid()
        )
    );

-- 作成ポリシー：認証済みユーザーが作成可能
CREATE POLICY "Authenticated users can create candidates" ON candidates
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM profiles
            WHERE profiles.id = auth.uid()
        )
    );

-- 更新ポリシー：管理者のみ
CREATE POLICY "Admin can update candidates" ON candidates
    FOR UPDATE USING (
        EXISTS (
            SELECT 1 FROM profiles
            WHERE profiles.id = auth.uid()
            AND profiles.role = 'admin'
        )
    );

-- 8. 追加の詳細情報テーブル（オプション）
-- より詳細な候補者情報が必要な場合は別テーブルで管理
CREATE TABLE IF NOT EXISTS candidate_details (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id UUID REFERENCES candidates(id) ON DELETE CASCADE,
    
    -- 詳細情報
    name TEXT,
    email TEXT,
    phone TEXT,
    current_position TEXT,
    experience_years INTEGER,
    skills TEXT[],
    education TEXT,
    
    -- スクレイピング時の生データ
    raw_html TEXT,
    parsed_data JSONB,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 9. 確認クエリ
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public' 
AND table_name = 'candidates'
ORDER BY ordinal_position;