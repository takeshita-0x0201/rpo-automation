-- ai_evaluationsテーブルの完全な再構築
-- 既存のテーブルを削除して、正しい構造で再作成

-- 1. 既存テーブルの削除（外部キー制約も含めて）
DROP TABLE IF EXISTS ai_evaluations CASCADE;

-- 2. 正しい構造でテーブルを再作成
CREATE TABLE ai_evaluations (
    -- 基本情報
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id UUID NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    requirement_id UUID NOT NULL REFERENCES job_requirements(id) ON DELETE CASCADE,
    search_id TEXT NOT NULL,  -- ジョブID（jobs.id）
    
    -- 評価結果
    ai_score FLOAT CHECK (ai_score >= 0 AND ai_score <= 100),  -- final_score
    match_score FLOAT CHECK (match_score >= 0 AND match_score <= 100),  -- final_scoreのコピー
    recommendation TEXT CHECK (recommendation IN ('A', 'B', 'C', 'D')),  -- final_judgment.recommendation
    confidence TEXT CHECK (confidence IN ('High', 'Medium', 'Low')),  -- final_confidence
    
    -- 詳細評価（配列形式）
    match_reasons TEXT[],     -- final_judgment.strengths
    concerns TEXT[],          -- final_judgment.concerns
    interview_points TEXT[],  -- final_judgment.interview_points
    overall_assessment TEXT,  -- final_judgment.overall_assessment
    
    -- メタデータ
    total_cycles INTEGER DEFAULT 0,      -- total_cycles
    total_searches INTEGER DEFAULT 0,    -- total_searches
    model_version TEXT DEFAULT 'gemini-1.5-pro',
    prompt_version TEXT DEFAULT '1.0',
    
    -- 詳細評価（JSON形式）- 後方互換性のため
    evaluation_result JSONB,  -- 全体の結果をJSONで保存
    
    -- タイムスタンプ
    evaluated_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. インデックスの作成
CREATE INDEX idx_ai_evaluations_candidate_id ON ai_evaluations(candidate_id);
CREATE INDEX idx_ai_evaluations_requirement_id ON ai_evaluations(requirement_id);
CREATE INDEX idx_ai_evaluations_search_id ON ai_evaluations(search_id);
CREATE INDEX idx_ai_evaluations_ai_score ON ai_evaluations(ai_score DESC);
CREATE INDEX idx_ai_evaluations_match_score ON ai_evaluations(match_score DESC);
CREATE INDEX idx_ai_evaluations_recommendation ON ai_evaluations(recommendation);
CREATE INDEX idx_ai_evaluations_confidence ON ai_evaluations(confidence);
CREATE INDEX idx_ai_evaluations_evaluated_at ON ai_evaluations(evaluated_at DESC);

-- 4. RLSポリシーの設定
ALTER TABLE ai_evaluations ENABLE ROW LEVEL SECURITY;

-- 全スタッフが閲覧可能
CREATE POLICY "Staff can view ai_evaluations" ON ai_evaluations
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM profiles
            WHERE profiles.id = auth.uid()
        )
    );

-- 認証済みユーザーが作成可能（AIマッチングサービス用）
CREATE POLICY "Authenticated users can create ai_evaluations" ON ai_evaluations
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM profiles
            WHERE profiles.id = auth.uid()
        )
    );

-- 管理者のみ更新可能
CREATE POLICY "Admin can update ai_evaluations" ON ai_evaluations
    FOR UPDATE USING (
        EXISTS (
            SELECT 1 FROM profiles
            WHERE profiles.id = auth.uid()
            AND profiles.role = 'admin'
        )
    );

-- 管理者のみ削除可能
CREATE POLICY "Admin can delete ai_evaluations" ON ai_evaluations
    FOR DELETE USING (
        EXISTS (
            SELECT 1 FROM profiles
            WHERE profiles.id = auth.uid()
            AND profiles.role = 'admin'
        )
    );

-- 5. updated_atトリガーの作成
CREATE OR REPLACE FUNCTION update_ai_evaluations_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_ai_evaluations_updated_at
    BEFORE UPDATE ON ai_evaluations
    FOR EACH ROW
    EXECUTE FUNCTION update_ai_evaluations_updated_at();

-- 6. コメントの追加
COMMENT ON TABLE ai_evaluations IS 'AI評価結果を保存するテーブル';
COMMENT ON COLUMN ai_evaluations.candidate_id IS '候補者ID';
COMMENT ON COLUMN ai_evaluations.requirement_id IS '採用要件ID';
COMMENT ON COLUMN ai_evaluations.search_id IS 'ジョブID（検索セッションID）';
COMMENT ON COLUMN ai_evaluations.ai_score IS 'AIスコア（0-100）';
COMMENT ON COLUMN ai_evaluations.match_score IS 'マッチスコア（ai_scoreと同じ値）';
COMMENT ON COLUMN ai_evaluations.recommendation IS '推奨度（A/B/C/D）';
COMMENT ON COLUMN ai_evaluations.confidence IS '確信度（High/Medium/Low）';
COMMENT ON COLUMN ai_evaluations.match_reasons IS '強み・マッチ理由';
COMMENT ON COLUMN ai_evaluations.concerns IS '懸念事項';
COMMENT ON COLUMN ai_evaluations.interview_points IS '面接確認ポイント';
COMMENT ON COLUMN ai_evaluations.overall_assessment IS '総合評価コメント';
COMMENT ON COLUMN ai_evaluations.evaluation_result IS '詳細評価結果（JSON形式）';

-- 7. テーブル構造の確認
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default,
    character_maximum_length
FROM information_schema.columns
WHERE table_schema = 'public' 
AND table_name = 'ai_evaluations'
ORDER BY ordinal_position;