-- 既存の関数を削除
DROP FUNCTION IF EXISTS get_next_job_id();

-- job_idカラムの型を変更（必要な場合）
ALTER TABLE jobs 
ALTER COLUMN job_id TYPE VARCHAR(10);

-- job-001形式のjob_idを生成する関数
CREATE OR REPLACE FUNCTION get_next_job_id()
RETURNS TEXT
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    next_val INTEGER;
    new_job_id TEXT;
BEGIN
    -- シーケンスから次の値を取得
    SELECT nextval('job_id_seq'::regclass) INTO next_val;
    
    -- job_idを生成 (job-001形式)
    new_job_id := 'job-' || LPAD(next_val::TEXT, 3, '0');
    
    RETURN new_job_id;
END;
$$;

-- 権限設定
GRANT EXECUTE ON FUNCTION get_next_job_id() TO authenticated;
GRANT EXECUTE ON FUNCTION get_next_job_id() TO service_role;

-- 既存のjob_idを更新（数値型の場合）
DO $$
DECLARE
    rec RECORD;
BEGIN
    -- 数値型のjob_idを持つレコードを更新
    FOR rec IN 
        SELECT id, job_id 
        FROM jobs 
        WHERE job_id IS NOT NULL 
        AND job_id::text ~ '^\d+$'  -- 数値のみの場合
        ORDER BY job_id::integer
    LOOP
        UPDATE jobs 
        SET job_id = 'job-' || LPAD(rec.job_id::TEXT, 3, '0')
        WHERE id = rec.id;
    END LOOP;
    
    -- シーケンスを最大値に更新
    PERFORM setval('job_id_seq', COALESCE(
        (SELECT MAX(CAST(SUBSTRING(job_id FROM 5) AS INTEGER)) 
         FROM jobs 
         WHERE job_id LIKE 'job-%'), 
        0
    ));
END $$;

-- インデックスを再作成
DROP INDEX IF EXISTS idx_jobs_job_id;
CREATE INDEX idx_jobs_job_id ON jobs(job_id);

-- コメント
COMMENT ON FUNCTION get_next_job_id() IS 'job-001形式のjob_idを生成する関数';