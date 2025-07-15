-- requirement_idの連番管理

-- 1. job_posting_idカラムの名前を変更（存在する場合）
ALTER TABLE job_requirements 
RENAME COLUMN job_posting_id TO requirement_id;

-- 2. カラムが存在しない場合は追加
ALTER TABLE job_requirements 
ADD COLUMN IF NOT EXISTS requirement_id TEXT UNIQUE;

-- 3. 連番管理用のテーブル
CREATE TABLE IF NOT EXISTS requirement_sequences (
    id SERIAL PRIMARY KEY,
    prefix TEXT NOT NULL DEFAULT 'req',
    current_number INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 4. 初期データの挿入
INSERT INTO requirement_sequences (prefix, current_number) 
VALUES ('req', 0) 
ON CONFLICT DO NOTHING;

-- 5. 連番取得用の関数
CREATE OR REPLACE FUNCTION get_next_requirement_id()
RETURNS TEXT AS $$
DECLARE
    next_id TEXT;
    next_number INTEGER;
BEGIN
    -- 現在の番号を取得して1増やす
    UPDATE requirement_sequences 
    SET current_number = current_number + 1,
        updated_at = NOW()
    WHERE prefix = 'req'
    RETURNING current_number INTO next_number;
    
    -- req-001形式のIDを生成
    next_id := 'req-' || LPAD(next_number::TEXT, 3, '0');
    
    RETURN next_id;
END;
$$ LANGUAGE plpgsql;

-- 6. インデックスの作成
CREATE INDEX IF NOT EXISTS idx_job_requirements_requirement_id ON job_requirements(requirement_id);