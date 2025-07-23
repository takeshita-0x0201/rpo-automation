-- ai_evaluationsテーブルの修正
-- evaluation_resultカラムを追加し、AIマッチングサービスと互換性を持たせる

-- 1. 既存テーブルが存在するか確認
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'ai_evaluations') THEN
        -- テーブルが存在しない場合は作成
        CREATE TABLE ai_evaluations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            candidate_id UUID NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
            requirement_id UUID REFERENCES job_requirements(id) ON DELETE CASCADE,
            search_id TEXT,  -- ジョブIDを参照
            ai_score FLOAT CHECK (ai_score >= 0 AND ai_score <= 100),  -- 0-100スケール
            match_score FLOAT CHECK (match_score >= 0 AND match_score <= 100),  -- 0-100スケール
            recommendation TEXT CHECK (recommendation IN ('A', 'B', 'C', 'D')),  -- A/B/C/D評価
            confidence TEXT CHECK (confidence IN ('High', 'Medium', 'Low')),
            match_reasons TEXT[],
            concerns TEXT[],
            evaluation_result JSONB,  -- 詳細評価結果（JSON形式）
            evaluated_at TIMESTAMPTZ DEFAULT NOW(),
            model_version TEXT,
            prompt_version TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );
        
        RAISE NOTICE 'ai_evaluations テーブルを作成しました';
    ELSE
        RAISE NOTICE 'ai_evaluations テーブルは既に存在します';
    END IF;
END $$;

-- 2. evaluation_resultカラムが存在しない場合は追加
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_name = 'ai_evaluations' AND column_name = 'evaluation_result'
    ) THEN
        ALTER TABLE ai_evaluations ADD COLUMN evaluation_result JSONB;
        RAISE NOTICE 'evaluation_result カラムを追加しました';
    ELSE
        RAISE NOTICE 'evaluation_result カラムは既に存在します';
    END IF;
END $$;

-- 3. match_scoreカラムが存在しない場合は追加
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_name = 'ai_evaluations' AND column_name = 'match_score'
    ) THEN
        ALTER TABLE ai_evaluations ADD COLUMN match_score FLOAT CHECK (match_score >= 0 AND match_score <= 100);
        RAISE NOTICE 'match_score カラムを追加しました';
    ELSE
        RAISE NOTICE 'match_score カラムは既に存在します';
    END IF;
END $$;

-- 4. confidenceカラムが存在しない場合は追加
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_name = 'ai_evaluations' AND column_name = 'confidence'
    ) THEN
        ALTER TABLE ai_evaluations ADD COLUMN confidence TEXT CHECK (confidence IN ('High', 'Medium', 'Low'));
        RAISE NOTICE 'confidence カラムを追加しました';
    ELSE
        RAISE NOTICE 'confidence カラムは既に存在します';
    END IF;
END $$;

-- 5. インデックスの作成
CREATE INDEX IF NOT EXISTS idx_ai_evaluations_candidate_id ON ai_evaluations(candidate_id);
CREATE INDEX IF NOT EXISTS idx_ai_evaluations_requirement_id ON ai_evaluations(requirement_id);
CREATE INDEX IF NOT EXISTS idx_ai_evaluations_search_id ON ai_evaluations(search_id);
CREATE INDEX IF NOT EXISTS idx_ai_evaluations_score ON ai_evaluations(ai_score DESC);
CREATE INDEX IF NOT EXISTS idx_ai_evaluations_match_score ON ai_evaluations(match_score DESC);
CREATE INDEX IF NOT EXISTS idx_ai_evaluations_recommendation ON ai_evaluations(recommendation);
CREATE INDEX IF NOT EXISTS idx_ai_evaluations_evaluated_at ON ai_evaluations(evaluated_at DESC);

-- 6. RLSポリシーの設定
ALTER TABLE ai_evaluations ENABLE ROW LEVEL SECURITY;

-- 全スタッフが閲覧可能
DROP POLICY IF EXISTS "Staff can view ai_evaluations" ON ai_evaluations;
CREATE POLICY "Staff can view ai_evaluations" ON ai_evaluations
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM profiles
            WHERE profiles.id = auth.uid()
        )
    );

-- 認証済みユーザーが作成可能（AIマッチングサービス用）
DROP POLICY IF EXISTS "Authenticated users can create ai_evaluations" ON ai_evaluations;
CREATE POLICY "Authenticated users can create ai_evaluations" ON ai_evaluations
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM profiles
            WHERE profiles.id = auth.uid()
        )
    );

-- 管理者のみ更新可能
DROP POLICY IF EXISTS "Admin can update ai_evaluations" ON ai_evaluations;
CREATE POLICY "Admin can update ai_evaluations" ON ai_evaluations
    FOR UPDATE USING (
        EXISTS (
            SELECT 1 FROM profiles
            WHERE profiles.id = auth.uid()
            AND profiles.role = 'admin'
        )
    );

-- 管理者のみ削除可能
DROP POLICY IF EXISTS "Admin can delete ai_evaluations" ON ai_evaluations;
CREATE POLICY "Admin can delete ai_evaluations" ON ai_evaluations
    FOR DELETE USING (
        EXISTS (
            SELECT 1 FROM profiles
            WHERE profiles.id = auth.uid()
            AND profiles.role = 'admin'
        )
    );

-- 7. テーブル構造の確認
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public' 
AND table_name = 'ai_evaluations'
ORDER BY ordinal_position;