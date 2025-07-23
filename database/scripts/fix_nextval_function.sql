-- 既存の関数を削除
DROP FUNCTION IF EXISTS nextval(text);

-- より安全なnextval関数を作成（パラメータ名を変更）
CREATE OR REPLACE FUNCTION nextval(seq_name text)
RETURNS bigint
LANGUAGE sql
SECURITY DEFINER
AS $$
    SELECT nextval(seq_name::regclass);
$$;

-- または、job_id専用の関数を作成する方法
CREATE OR REPLACE FUNCTION get_next_job_id()
RETURNS integer
LANGUAGE sql
SECURITY DEFINER
AS $$
    SELECT nextval('job_id_seq'::regclass)::integer;
$$;

-- 権限設定
GRANT EXECUTE ON FUNCTION nextval(text) TO authenticated;
GRANT EXECUTE ON FUNCTION nextval(text) TO service_role;
GRANT EXECUTE ON FUNCTION get_next_job_id() TO authenticated;
GRANT EXECUTE ON FUNCTION get_next_job_id() TO service_role;

-- コメント
COMMENT ON FUNCTION get_next_job_id() IS 'job_idシーケンスの次の値を取得する専用関数';