-- 既存の制約を削除（存在する場合）
ALTER TABLE clients DROP CONSTRAINT IF EXISTS clients_company_id_unique;

-- company_idの連番生成用シーケンスを作成
DROP SEQUENCE IF EXISTS company_id_seq CASCADE;
CREATE SEQUENCE company_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    CACHE 1;

-- company_id生成関数（修正版）
CREATE OR REPLACE FUNCTION generate_company_id()
RETURNS TEXT
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    next_val INTEGER;
    new_company_id TEXT;
BEGIN
    -- シーケンスから次の値を取得
    SELECT nextval('company_id_seq') INTO next_val;
    
    -- company_idを生成
    new_company_id := 'comp-' || LPAD(next_val::TEXT, 3, '0');
    
    RETURN new_company_id;
END;
$$;

-- 権限設定
GRANT EXECUTE ON FUNCTION generate_company_id() TO authenticated;
GRANT EXECUTE ON FUNCTION generate_company_id() TO service_role;

-- clientsテーブルのcompany_idをUNIQUEに設定
ALTER TABLE clients 
ADD CONSTRAINT clients_company_id_unique UNIQUE (company_id);

-- 既存のレコードに連番を割り当てる（一度に実行）
DO $$
DECLARE
    rec RECORD;
    counter INTEGER := 1;
BEGIN
    FOR rec IN 
        SELECT id 
        FROM clients 
        WHERE company_id IS NULL OR company_id = '' OR company_id LIKE 'req-temp-%'
        ORDER BY created_at
    LOOP
        UPDATE clients 
        SET company_id = 'comp-' || LPAD(counter::TEXT, 3, '0')
        WHERE id = rec.id;
        
        counter := counter + 1;
    END LOOP;
    
    -- シーケンスを更新された最大値に設定
    PERFORM setval('company_id_seq', COALESCE(
        (SELECT MAX(CAST(SUBSTRING(company_id FROM 6) AS INTEGER)) 
         FROM clients 
         WHERE company_id LIKE 'comp-%'), 
        0
    ));
END $$;

-- コメント追加
COMMENT ON FUNCTION generate_company_id() IS 'comp-001形式のcompany_idを生成する関数';
COMMENT ON SEQUENCE company_id_seq IS 'company_id生成用のシーケンス';