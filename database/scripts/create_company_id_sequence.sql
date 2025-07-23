-- company_idの連番生成用シーケンスを作成
CREATE SEQUENCE IF NOT EXISTS company_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    CACHE 1;

-- company_id生成関数
CREATE OR REPLACE FUNCTION generate_company_id()
RETURNS TEXT
LANGUAGE plpgsql
AS $$
DECLARE
    next_val INTEGER;
BEGIN
    next_val := nextval('company_id_seq');
    RETURN 'comp-' || LPAD(next_val::TEXT, 3, '0');
END;
$$;

-- clientsテーブルのcompany_idをUNIQUEに設定（まだの場合）
ALTER TABLE clients 
ADD CONSTRAINT clients_company_id_unique UNIQUE (company_id);

-- 既存のclientsレコードにcompany_idを割り当て（必要な場合）
UPDATE clients 
SET company_id = generate_company_id()
WHERE company_id IS NULL OR company_id = '';

-- コメント追加
COMMENT ON FUNCTION generate_company_id() IS 'comp-001形式のcompany_idを生成する関数';
COMMENT ON SEQUENCE company_id_seq IS 'company_id生成用のシーケンス';