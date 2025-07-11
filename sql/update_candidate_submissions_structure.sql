-- candidate_submissionsテーブルの構造を更新
-- 送客データの詳細をJSONBで保存し、GAS連携用のデータも含める

-- 既存のcandidate_submissionsテーブルにカラムを追加
ALTER TABLE candidate_submissions
ADD COLUMN IF NOT EXISTS submitted_by UUID REFERENCES profiles(id),
ADD COLUMN IF NOT EXISTS submission_data JSONB,
ADD COLUMN IF NOT EXISTS sheets_url TEXT,
ADD COLUMN IF NOT EXISTS gas_webhook_sent BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS gas_webhook_response JSONB;

-- インデックスを追加
CREATE INDEX IF NOT EXISTS idx_candidate_submissions_submitted_by ON candidate_submissions(submitted_by);
CREATE INDEX IF NOT EXISTS idx_candidate_submissions_submitted_at ON candidate_submissions(submitted_at DESC);
CREATE INDEX IF NOT EXISTS idx_candidate_submissions_status ON candidate_submissions(status);

-- コメントを追加
COMMENT ON COLUMN candidate_submissions.submission_data IS '送客時の候補者情報とAI評価のスナップショット';
COMMENT ON COLUMN candidate_submissions.sheets_url IS 'Google SheetsのURL（GASから返却される）';
COMMENT ON COLUMN candidate_submissions.gas_webhook_sent IS 'GAS webhookへの送信フラグ';
COMMENT ON COLUMN candidate_submissions.gas_webhook_response IS 'GASからのレスポンス';