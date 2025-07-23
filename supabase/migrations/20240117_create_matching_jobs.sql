-- マッチングジョブ管理テーブル
CREATE TABLE matching_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    requirement_id UUID NOT NULL REFERENCES job_requirements(id) ON DELETE CASCADE,
    candidate_id UUID NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- ジョブステータス
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'cancelled')),
    progress INTEGER DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
    
    -- 処理詳細
    current_stage TEXT, -- 'evaluation', 'gap_analysis', 'research', 'report_generation'
    current_cycle INTEGER DEFAULT 0,
    max_cycles INTEGER DEFAULT 3,
    
    -- 結果
    result JSONB,
    error_message TEXT,
    
    -- タイムスタンプ
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    
    -- インデックス
    INDEX idx_matching_jobs_status (status),
    INDEX idx_matching_jobs_user (user_id),
    INDEX idx_matching_jobs_created (created_at DESC)
);

-- マッチング結果詳細テーブル
CREATE TABLE matching_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES matching_jobs(id) ON DELETE CASCADE,
    
    -- 最終評価
    final_score INTEGER CHECK (final_score >= 0 AND final_score <= 100),
    recommendation CHAR(1) CHECK (recommendation IN ('A', 'B', 'C', 'D')),
    confidence TEXT CHECK (confidence IN ('Low', 'Medium', 'High')),
    
    -- 詳細分析
    strengths JSONB, -- 強みのリスト
    concerns JSONB,  -- 懸念点のリスト
    interview_points JSONB, -- 面接確認事項
    
    -- 評価履歴
    evaluation_history JSONB, -- 各サイクルの詳細
    search_results JSONB,     -- 追加調査結果
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    INDEX idx_matching_results_job (job_id)
);

-- RLSポリシー設定
ALTER TABLE matching_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE matching_results ENABLE ROW LEVEL SECURITY;

-- ユーザーは自分のジョブのみアクセス可能
CREATE POLICY "Users can view own matching jobs" ON matching_jobs
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can create own matching jobs" ON matching_jobs
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own matching jobs" ON matching_jobs
    FOR UPDATE USING (auth.uid() = user_id);

-- 結果も同様
CREATE POLICY "Users can view own matching results" ON matching_results
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM matching_jobs 
            WHERE matching_jobs.id = matching_results.job_id 
            AND matching_jobs.user_id = auth.uid()
        )
    );

-- リアルタイム購読用の関数
CREATE OR REPLACE FUNCTION notify_job_status_change()
RETURNS TRIGGER AS $$
BEGIN
    PERFORM pg_notify(
        'matching_job_update',
        json_build_object(
            'job_id', NEW.id,
            'status', NEW.status,
            'progress', NEW.progress
        )::text
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- トリガー設定
CREATE TRIGGER matching_job_status_trigger
    AFTER UPDATE OF status, progress ON matching_jobs
    FOR EACH ROW
    EXECUTE FUNCTION notify_job_status_change();