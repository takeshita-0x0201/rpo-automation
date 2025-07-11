-- candidatesテーブルを新しい構造で作成するSQL（既存データなし版）
-- 実行日: 2025-07-10

-- 1. 既存のcandidatesテーブルを削除（存在する場合）
DROP TABLE IF EXISTS candidates CASCADE;

-- 2. candidatesテーブルを新規作成
CREATE TABLE candidates (
    -- 基本カラム
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- スクレイピングデータカラム（必須）
    candidate_id TEXT NOT NULL,
    candidate_link TEXT NOT NULL,
    candidate_company TEXT,
    candidate_resume TEXT,
    platform TEXT NOT NULL DEFAULT 'bizreach',
    
    -- メタデータ
    scraped_at TIMESTAMPTZ DEFAULT NOW(),
    scraped_by UUID REFERENCES profiles(id),
    
    -- リレーション
    client_id UUID NOT NULL REFERENCES clients(id),
    requirement_id UUID NOT NULL REFERENCES job_requirements(id),
    scraping_session_id UUID REFERENCES scraping_sessions(id),
    
    -- ユニーク制約
    CONSTRAINT unique_candidate_per_platform UNIQUE (candidate_id, platform)
);

-- 3. インデックスの作成
CREATE INDEX idx_candidates_candidate_id ON candidates(candidate_id);
CREATE INDEX idx_candidates_platform ON candidates(platform);
CREATE INDEX idx_candidates_company ON candidates(candidate_company);
CREATE INDEX idx_candidates_client ON candidates(client_id);
CREATE INDEX idx_candidates_requirement ON candidates(requirement_id);
CREATE INDEX idx_candidates_session ON candidates(scraping_session_id);
CREATE INDEX idx_candidates_scraped_at ON candidates(scraped_at DESC);

-- 4. updated_atトリガーの作成
CREATE TRIGGER update_candidates_updated_at
    BEFORE UPDATE ON candidates
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- 5. RLSポリシーの設定
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

-- 削除ポリシー：管理者のみ
CREATE POLICY "Admin can delete candidates" ON candidates
    FOR DELETE USING (
        EXISTS (
            SELECT 1 FROM profiles
            WHERE profiles.id = auth.uid()
            AND profiles.role = 'admin'
        )
    );

-- 6. コメントの追加
COMMENT ON TABLE candidates IS 'スクレイピングした候補者データを格納するテーブル';
COMMENT ON COLUMN candidates.candidate_id IS 'プラットフォーム上の候補者ID（例：Bizreach ID）';
COMMENT ON COLUMN candidates.candidate_link IS '候補者プロフィールページへのURL';
COMMENT ON COLUMN candidates.candidate_company IS '候補者の現在の所属企業名';
COMMENT ON COLUMN candidates.candidate_resume IS 'レジュメ情報（テキストまたはPDF URL）';
COMMENT ON COLUMN candidates.platform IS 'スクレイピング元プラットフォーム';
COMMENT ON COLUMN candidates.scraped_at IS 'スクレイピング実行日時';
COMMENT ON COLUMN candidates.scraped_by IS 'スクレイピング実行者';
COMMENT ON COLUMN candidates.client_id IS 'クライアントID';
COMMENT ON COLUMN candidates.requirement_id IS '採用要件ID';
COMMENT ON COLUMN candidates.scraping_session_id IS 'スクレイピングセッションID';

-- 7. テーブル構造の確認
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public' 
AND table_name = 'candidates'
ORDER BY ordinal_position;