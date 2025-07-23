-- requirement_idの連番生成用シーケンスを作成
DROP SEQUENCE IF EXISTS requirement_id_seq CASCADE;
CREATE SEQUENCE requirement_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    CACHE 1;

-- requirement_id生成関数
CREATE OR REPLACE FUNCTION get_next_requirement_id()
RETURNS TEXT
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    next_val INTEGER;
    new_requirement_id TEXT;
BEGIN
    -- シーケンスから次の値を取得
    SELECT nextval('requirement_id_seq') INTO next_val;
    
    -- requirement_idを生成 (req-001形式)
    new_requirement_id := 'req-' || LPAD(next_val::TEXT, 3, '0');
    
    RETURN new_requirement_id;
END;
$$;

-- 権限設定
GRANT EXECUTE ON FUNCTION get_next_requirement_id() TO authenticated;
GRANT EXECUTE ON FUNCTION get_next_requirement_id() TO service_role;

-- job_requirementsテーブルにrequirement_idカラムが存在しない場合は追加
ALTER TABLE job_requirements 
ADD COLUMN IF NOT EXISTS requirement_id VARCHAR(10) UNIQUE;

-- 既存のレコードに連番を割り当てる
DO $$
DECLARE
    rec RECORD;
    counter INTEGER := 1;
BEGIN
    FOR rec IN 
        SELECT id 
        FROM job_requirements 
        WHERE requirement_id IS NULL OR requirement_id = '' OR requirement_id LIKE 'req-temp-%'
        ORDER BY created_at
    LOOP
        UPDATE job_requirements 
        SET requirement_id = 'req-' || LPAD(counter::TEXT, 3, '0')
        WHERE id = rec.id;
        
        counter := counter + 1;
    END LOOP;
    
    -- シーケンスを更新された最大値に設定
    PERFORM setval('requirement_id_seq', COALESCE(
        (SELECT MAX(CAST(SUBSTRING(requirement_id FROM 5) AS INTEGER)) 
         FROM job_requirements 
         WHERE requirement_id LIKE 'req-%'), 
        0
    ));
END $$;

-- インデックスを作成
CREATE INDEX IF NOT EXISTS idx_job_requirements_requirement_id ON job_requirements(requirement_id);

-- コメント追加
COMMENT ON FUNCTION get_next_requirement_id() IS 'req-001形式のrequirement_idを生成する関数';
COMMENT ON SEQUENCE requirement_id_seq IS 'requirement_id生成用のシーケンス';
COMMENT ON COLUMN job_requirements.requirement_id IS '採用要件の連番ID（req-001形式）';