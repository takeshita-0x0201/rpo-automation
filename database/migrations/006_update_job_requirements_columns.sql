-- job_requirementsテーブルに求人票と求人メモのカラムを追加

-- 求人票カラムを追加
ALTER TABLE job_requirements 
ADD COLUMN IF NOT EXISTS job_description TEXT;

-- 求人メモカラムを追加
ALTER TABLE job_requirements 
ADD COLUMN IF NOT EXISTS memo TEXT;

-- job_posting_idカラムが存在しない場合は追加
ALTER TABLE job_requirements 
ADD COLUMN IF NOT EXISTS job_posting_id TEXT;

-- 連番管理用のシーケンステーブル（既存のものを使用）
-- job_posting_sequencesテーブルが存在しない場合は作成
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

-- 連番取得用の関数（既存のものを使用）
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