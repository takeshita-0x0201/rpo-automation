-- job_idの連番生成用シーケンスを作成
CREATE SEQUENCE IF NOT EXISTS job_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    CACHE 1;

-- jobsテーブルにjob_idカラムを追加（まだ存在しない場合）
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'jobs' 
        AND column_name = 'job_id'
    ) THEN
        ALTER TABLE jobs ADD COLUMN job_id INTEGER UNIQUE;
        
        -- 既存のレコードに連番を割り当て
        UPDATE jobs 
        SET job_id = nextval('job_id_seq')
        WHERE job_id IS NULL
        ORDER BY created_at;
    END IF;
END $$;

-- job_idにインデックスを作成
CREATE INDEX IF NOT EXISTS idx_jobs_job_id ON jobs(job_id);

-- コメント追加
COMMENT ON COLUMN jobs.job_id IS '連番のジョブID（表示用）';
COMMENT ON SEQUENCE job_id_seq IS 'job_id生成用のシーケンス';