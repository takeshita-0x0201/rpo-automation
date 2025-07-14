-- 求人票マスタテーブルの作成
-- ポジション、求人票、メモを正規化して管理

CREATE TABLE IF NOT EXISTS job_postings (
    id TEXT PRIMARY KEY,  -- req-001形式の連番ID
    position TEXT NOT NULL,  -- ポジション名
    job_description TEXT NOT NULL,  -- 求人票全文
    memo TEXT,  -- 求人メモ（補足情報）
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by UUID REFERENCES users(id)
);

-- インデックスの作成
CREATE INDEX idx_job_postings_position ON job_postings(position);
CREATE INDEX idx_job_postings_created_at ON job_postings(created_at);

-- job_requirementsテーブルに求人票への参照を追加
ALTER TABLE job_requirements 
ADD COLUMN IF NOT EXISTS job_posting_id TEXT REFERENCES job_postings(id);

-- 連番管理用のシーケンステーブル
CREATE TABLE IF NOT EXISTS job_posting_sequences (
    id SERIAL PRIMARY KEY,
    prefix TEXT NOT NULL DEFAULT 'req',
    current_number INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 初期データの挿入
INSERT INTO job_posting_sequences (prefix, current_number) 
VALUES ('req', 0) 
ON CONFLICT DO NOTHING;

-- 連番取得用の関数
CREATE OR REPLACE FUNCTION get_next_job_posting_id()
RETURNS TEXT AS $$
DECLARE
    next_id TEXT;
    next_number INTEGER;
BEGIN
    -- 現在の番号を取得して1増やす
    UPDATE job_posting_sequences 
    SET current_number = current_number + 1,
        updated_at = NOW()
    WHERE prefix = 'req'
    RETURNING current_number INTO next_number;
    
    -- req-001形式のIDを生成
    next_id := 'req-' || LPAD(next_number::TEXT, 3, '0');
    
    RETURN next_id;
END;
$$ LANGUAGE plpgsql;

-- RLSポリシーの設定
ALTER TABLE job_postings ENABLE ROW LEVEL SECURITY;

-- 全ユーザーが読み取り可能
CREATE POLICY "job_postings_read" ON job_postings
    FOR SELECT USING (true);

-- 管理者とマネージャーのみが作成・更新・削除可能
CREATE POLICY "job_postings_write" ON job_postings
    FOR ALL USING (
        auth.uid() IN (
            SELECT id FROM users 
            WHERE role IN ('admin', 'manager')
        )
    );