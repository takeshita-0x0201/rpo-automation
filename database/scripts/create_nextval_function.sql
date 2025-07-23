-- nextval関数を作成（Supabase RPCで使用）
CREATE OR REPLACE FUNCTION nextval(sequence_name text)
RETURNS integer
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN nextval(sequence_name);
END;
$$;

-- 関数の実行権限を設定
GRANT EXECUTE ON FUNCTION nextval(text) TO authenticated;
GRANT EXECUTE ON FUNCTION nextval(text) TO service_role;

-- コメント追加
COMMENT ON FUNCTION nextval(text) IS 'シーケンスの次の値を取得する関数';