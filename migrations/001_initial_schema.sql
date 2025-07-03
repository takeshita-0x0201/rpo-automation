-- Supabase用初期スキーマ
-- 注意: Supabase Authは既に組み込まれているため、独自のusersテーブルは不要

-- RPOスタッフプロファイルテーブル
CREATE TABLE profiles (
    id UUID REFERENCES auth.users(id) PRIMARY KEY,
    full_name TEXT,
    role TEXT CHECK (role IN ('admin', 'manager', 'operator')),
    department TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW())
);

-- クライアント企業テーブル
CREATE TABLE clients (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name TEXT NOT NULL,
    industry TEXT,
    size TEXT,
    contact_person TEXT,
    contact_email TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW())
);

-- ジョブテーブル
CREATE TABLE jobs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    requirement_id TEXT NOT NULL,
    client_id UUID REFERENCES clients(id),
    status TEXT CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    created_by UUID REFERENCES auth.users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW()),
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    candidate_count INTEGER DEFAULT 0
);

-- ジョブステータス履歴
CREATE TABLE job_status_history (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    job_id UUID REFERENCES jobs(id),
    status TEXT NOT NULL,
    message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW())
);

-- リトライキュー
CREATE TABLE retry_queue (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    job_id UUID REFERENCES jobs(id),
    retry_count INTEGER DEFAULT 0,
    next_retry_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW())
);

-- クライアント設定
CREATE TABLE client_settings (
    client_id UUID REFERENCES clients(id) PRIMARY KEY,
    search_defaults JSONB DEFAULT '{}',
    scoring_weights JSONB DEFAULT '{}',
    custom_terms JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW())
);

-- 候補者送客履歴
CREATE TABLE candidate_submissions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    job_id UUID REFERENCES jobs(id),
    client_id UUID REFERENCES clients(id),
    candidate_id TEXT NOT NULL,
    submitted_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW()),
    status TEXT CHECK (status IN ('submitted', 'reviewing', 'accepted', 'rejected')),
    client_feedback TEXT
);

-- 通知設定
CREATE TABLE notification_settings (
    user_id UUID REFERENCES auth.users(id) PRIMARY KEY,
    email_enabled BOOLEAN DEFAULT true,
    slack_webhook_url TEXT,
    notify_on_complete BOOLEAN DEFAULT true,
    notify_on_error BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW())
);

-- Row Level Security (RLS) の有効化
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE clients ENABLE ROW LEVEL SECURITY;
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_status_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE retry_queue ENABLE ROW LEVEL SECURITY;
ALTER TABLE client_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE notification_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE candidate_submissions ENABLE ROW LEVEL SECURITY;

-- RLSポリシー設定
-- スタッフは自分のプロファイルのみ更新可能
CREATE POLICY "Staff can view all profiles" ON profiles FOR SELECT USING (true);
CREATE POLICY "Staff can update own profile" ON profiles FOR UPDATE USING (auth.uid() = id);

-- 全スタッフが全クライアントデータを参照可能
CREATE POLICY "Staff can view all clients" ON clients FOR SELECT USING (true);
CREATE POLICY "Staff can manage clients" ON clients FOR ALL USING (EXISTS (
    SELECT 1 FROM profiles WHERE id = auth.uid() AND role IN ('admin', 'manager')
));

-- ジョブは全スタッフが参照可能
CREATE POLICY "Staff can view all jobs" ON jobs FOR SELECT USING (true);
CREATE POLICY "Staff can manage jobs" ON jobs FOR ALL USING (true);

-- 候補者送客履歴も全スタッフが参照可能
CREATE POLICY "Staff can view all submissions" ON candidate_submissions FOR SELECT USING (true);
CREATE POLICY "Staff can manage submissions" ON candidate_submissions FOR ALL USING (true);

-- 通知設定は本人のみ
CREATE POLICY "Users can view own notification settings" ON notification_settings FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can update own notification settings" ON notification_settings FOR UPDATE USING (auth.uid() = user_id);

-- トリガー: updated_atの自動更新
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = TIMEZONE('utc', NOW());
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_profiles_updated_at BEFORE UPDATE ON profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_clients_updated_at BEFORE UPDATE ON clients
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_jobs_updated_at BEFORE UPDATE ON jobs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_client_settings_updated_at BEFORE UPDATE ON client_settings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_notification_settings_updated_at BEFORE UPDATE ON notification_settings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();