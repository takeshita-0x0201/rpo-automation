# Supabaseセットアップガイド

このガイドでは、RPO自動化システムで使用するSupabaseプロジェクトの詳細なセットアップ手順を説明します。

## 目次

- [Supabaseアカウントの作成](#supabaseアカウントの作成)
- [プロジェクトの作成](#プロジェクトの作成)
- [データベーススキーマの作成](#データベーススキーマの作成)
- [認証設定](#認証設定)
- [Row Level Security (RLS) の設定](#row-level-security-rls-の設定)
- [接続テスト](#接続テスト)
- [初期データの投入](#初期データの投入)
- [バックアップ設定](#バックアップ設定)

---

## Supabaseアカウントの作成

### 1. アカウント登録

1. [Supabase公式サイト](https://supabase.com)にアクセス
2. 「Start your project」をクリック
3. 以下のいずれかでサインアップ：
   - GitHubアカウント（推奨）
   - メールアドレス

### 2. 料金プランの選択

開発・テスト用途では**Freeプラン**で十分です：

| 項目 | Freeプラン | Proプラン |
|------|-----------|-----------|
| データベース容量 | 500MB | 8GB |
| 認証ユーザー数 | 50,000 | 100,000 |
| リアルタイム接続 | 200 | 500 |
| ストレージ | 1GB | 100GB |

---

## プロジェクトの作成

### 1. 新規プロジェクトの作成

1. Supabaseダッシュボードで「New project」をクリック
2. 以下の情報を入力：

```
プロジェクト名: rpo-automation
データベースパスワード: [安全なパスワードを設定]
リージョン: Northeast Asia (Tokyo) - ap-northeast-1
```

3. 「Create new project」をクリック
4. プロジェクトの初期化完了まで約2分待機

### 2. プロジェクト情報の取得

プロジェクト作成後、以下の情報を「Settings」→「API」から取得：

```bash
# プロジェクトURL
Project URL: https://xxxxxxxxxxxxx.supabase.co

# API Keys
anon public: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
service_role secret: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**重要:** `service_role`キーは管理者権限を持つため、安全に管理してください。

---

## データベーススキーマの作成

### 1. SQL Editorでのテーブル作成

Supabaseダッシュボードの「SQL Editor」を開き、以下のSQLを実行します。

#### 基本テーブルの作成

```sql
-- profiles（ユーザープロファイル）
CREATE TABLE IF NOT EXISTS profiles (
    id UUID REFERENCES auth.users(id) PRIMARY KEY,
    full_name TEXT,
    role TEXT CHECK (role IN ('admin', 'user')) DEFAULT 'user',
    department TEXT,
    avatar_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- clients（クライアント企業）
CREATE TABLE IF NOT EXISTS clients (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name TEXT NOT NULL,
    industry TEXT,
    size TEXT,
    contact_person TEXT,
    contact_email TEXT,
    bizreach_search_url TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- client_settings（クライアント別設定）
CREATE TABLE IF NOT EXISTS client_settings (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
    setting_key TEXT NOT NULL,
    setting_value JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(client_id, setting_key)
);

-- job_requirements（採用要件マスター）
CREATE TABLE IF NOT EXISTS job_requirements (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    structured_data JSONB,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID REFERENCES profiles(id),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- search_jobs（検索・AIマッチングジョブ）
CREATE TABLE IF NOT EXISTS search_jobs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
    job_type TEXT CHECK (job_type IN ('scraping', 'ai_matching')) NOT NULL,
    status TEXT CHECK (status IN ('pending', 'in_progress', 'completed', 'failed')) DEFAULT 'pending',
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    total_candidates_processed INTEGER DEFAULT 0,
    job_parameters JSONB,
    error_details TEXT
);

-- job_status_history（ジョブステータス履歴）
CREATE TABLE IF NOT EXISTS job_status_history (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    job_id UUID REFERENCES search_jobs(id) ON DELETE CASCADE,
    status TEXT NOT NULL,
    message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- candidates（候補者マスター）
CREATE TABLE IF NOT EXISTS candidates (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    bizreach_url TEXT UNIQUE,
    name TEXT,
    email TEXT UNIQUE,
    phone TEXT,
    current_company TEXT,
    current_position TEXT,
    experience_years INTEGER,
    skills TEXT[],
    education TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- candidate_submissions（候補者データ提出履歴）
CREATE TABLE IF NOT EXISTS candidate_submissions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    candidate_id UUID REFERENCES candidates(id) ON DELETE CASCADE,
    search_job_id UUID REFERENCES search_jobs(id) ON DELETE CASCADE,
    submission_time TIMESTAMPTZ DEFAULT NOW(),
    source TEXT,
    raw_data JSONB,
    submitted_by_user_id UUID REFERENCES profiles(id)
);

-- search_results（検索結果）
CREATE TABLE IF NOT EXISTS search_results (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    search_job_id UUID REFERENCES search_jobs(id) ON DELETE CASCADE,
    candidate_id UUID REFERENCES candidates(id) ON DELETE CASCADE,
    job_requirement_id UUID REFERENCES job_requirements(id) ON DELETE CASCADE,
    match_score FLOAT,
    match_reasons TEXT[],
    ai_evaluation_details JSONB,
    evaluated_at TIMESTAMPTZ DEFAULT NOW()
);

-- notification_settings（通知設定）
CREATE TABLE IF NOT EXISTS notification_settings (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    profile_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    notification_type TEXT CHECK (notification_type IN ('email', 'in_app', 'slack')),
    enabled BOOLEAN DEFAULT true,
    frequency TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- retry_queue（リトライキュー）
CREATE TABLE IF NOT EXISTS retry_queue (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    operation_type TEXT NOT NULL,
    payload JSONB NOT NULL,
    retries_attempted INTEGER DEFAULT 0,
    last_attempt_at TIMESTAMPTZ,
    next_retry_at TIMESTAMPTZ NOT NULL,
    status TEXT CHECK (status IN ('pending', 'retrying', 'failed', 'completed')) DEFAULT 'pending',
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### インデックスの作成

```sql
-- パフォーマンス向上のためのインデックス
CREATE INDEX IF NOT EXISTS idx_clients_is_active ON clients(is_active);
CREATE INDEX IF NOT EXISTS idx_job_requirements_client_id ON job_requirements(client_id);
CREATE INDEX IF NOT EXISTS idx_job_requirements_is_active ON job_requirements(is_active);
CREATE INDEX IF NOT EXISTS idx_search_jobs_user_id ON search_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_search_jobs_status ON search_jobs(status);
CREATE INDEX IF NOT EXISTS idx_candidates_bizreach_url ON candidates(bizreach_url);
CREATE INDEX IF NOT EXISTS idx_search_results_job_id ON search_results(search_job_id);
CREATE INDEX IF NOT EXISTS idx_retry_queue_status ON retry_queue(status);
CREATE INDEX IF NOT EXISTS idx_retry_queue_next_retry ON retry_queue(next_retry_at);
```

#### トリガー関数の作成

```sql
-- updated_at自動更新のためのトリガー関数
CREATE OR REPLACE FUNCTION handle_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 各テーブルにトリガーを設定
CREATE TRIGGER trigger_profiles_updated_at
    BEFORE UPDATE ON profiles
    FOR EACH ROW EXECUTE FUNCTION handle_updated_at();

CREATE TRIGGER trigger_clients_updated_at
    BEFORE UPDATE ON clients
    FOR EACH ROW EXECUTE FUNCTION handle_updated_at();

CREATE TRIGGER trigger_client_settings_updated_at
    BEFORE UPDATE ON client_settings
    FOR EACH ROW EXECUTE FUNCTION handle_updated_at();

CREATE TRIGGER trigger_job_requirements_updated_at
    BEFORE UPDATE ON job_requirements
    FOR EACH ROW EXECUTE FUNCTION handle_updated_at();

CREATE TRIGGER trigger_candidates_updated_at
    BEFORE UPDATE ON candidates
    FOR EACH ROW EXECUTE FUNCTION handle_updated_at();

CREATE TRIGGER trigger_notification_settings_updated_at
    BEFORE UPDATE ON notification_settings
    FOR EACH ROW EXECUTE FUNCTION handle_updated_at();

CREATE TRIGGER trigger_retry_queue_updated_at
    BEFORE UPDATE ON retry_queue
    FOR EACH ROW EXECUTE FUNCTION handle_updated_at();
```

### 2. テーブル作成の確認

テーブルが正しく作成されたかを確認：

```sql
-- 作成されたテーブル一覧の確認
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;

-- 各テーブルのカラム情報確認
SELECT table_name, column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
ORDER BY table_name, ordinal_position;
```

---

## 認証設定

### 1. 認証プロバイダーの設定

1. 「Authentication」→「Settings」を開く
2. 以下の設定を確認・変更：

```
Site URL: http://localhost:8000 (開発環境)
Additional Redirect URLs: 
- http://localhost:8000/auth/callback
- https://your-domain.com/auth/callback (本番環境)

Email Auth: 有効
Auto Confirm: 無効 (本番環境では無効推奨)
```

### 2. メールテンプレートの設定

「Authentication」→「Email Templates」でメールテンプレートをカスタマイズ：

```html
<!-- 確認メールテンプレート例 -->
<h2>RPO自動化システムへようこそ</h2>
<p>以下のリンクをクリックしてアカウントを有効化してください：</p>
<a href="{{ .ConfirmationURL }}">アカウントを有効化</a>
```

### 3. セキュリティ設定

```
Session timeout: 24 hours
Password minimum length: 8
Require email confirmation: true
```

---

## Row Level Security (RLS) の設定

Supabaseの重要なセキュリティ機能であるRLSを設定します。

### 1. RLSの有効化

```sql
-- 全テーブルでRLSを有効化
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE clients ENABLE ROW LEVEL SECURITY;
ALTER TABLE client_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_requirements ENABLE ROW LEVEL SECURITY;
ALTER TABLE search_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_status_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE candidates ENABLE ROW LEVEL SECURITY;
ALTER TABLE candidate_submissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE search_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE notification_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE retry_queue ENABLE ROW LEVEL SECURITY;
```

### 2. RLSポリシーの作成

```sql
-- profiles: 本人のみ更新、adminは全て閲覧可能
CREATE POLICY "Users can view own profile" ON profiles
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can update own profile" ON profiles
    FOR UPDATE USING (auth.uid() = id);

CREATE POLICY "Admins can view all profiles" ON profiles
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM profiles 
            WHERE id = auth.uid() AND role = 'admin'
        )
    );

-- clients: 全スタッフが閲覧、adminのみ編集
CREATE POLICY "All authenticated users can view clients" ON clients
    FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "Only admins can modify clients" ON clients
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM profiles 
            WHERE id = auth.uid() AND role = 'admin'
        )
    );

-- job_requirements: 関連クライアントのスタッフが閲覧・編集
CREATE POLICY "Users can view requirements" ON job_requirements
    FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "Users can insert requirements" ON job_requirements
    FOR INSERT WITH CHECK (
        auth.uid() = created_by AND
        auth.role() = 'authenticated'
    );

CREATE POLICY "Users can update own requirements" ON job_requirements
    FOR UPDATE USING (
        auth.uid() = created_by OR
        EXISTS (
            SELECT 1 FROM profiles 
            WHERE id = auth.uid() AND role = 'admin'
        )
    );

-- search_jobs: 本人のジョブのみ閲覧
CREATE POLICY "Users can view own jobs" ON search_jobs
    FOR SELECT USING (
        auth.uid() = user_id OR
        EXISTS (
            SELECT 1 FROM profiles 
            WHERE id = auth.uid() AND role = 'admin'
        )
    );

CREATE POLICY "Users can insert own jobs" ON search_jobs
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own jobs" ON search_jobs
    FOR UPDATE USING (
        auth.uid() = user_id OR
        EXISTS (
            SELECT 1 FROM profiles 
            WHERE id = auth.uid() AND role = 'admin'
        )
    );

-- candidates: 全スタッフが閲覧、管理者のみ編集
CREATE POLICY "All authenticated users can view candidates" ON candidates
    FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "Only admins can modify candidates" ON candidates
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM profiles 
            WHERE id = auth.uid() AND role = 'admin'
        )
    );

-- 他のテーブルも同様にポリシーを設定...
```

### 3. サービスロール用の特別権限

```sql
-- サービスロール（service_role）は全てのポリシーをバイパス
-- これによりバックエンドAPIから全データにアクセス可能
```

---

## 接続テスト

### 1. Python クライアントでの接続テスト

```python
# test_supabase_connection.py
import os
from dotenv import load_dotenv
from supabase import create_client, Client

def test_connection():
    load_dotenv()
    
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY")
    
    print(f"Connecting to: {url}")
    
    try:
        supabase: Client = create_client(url, key)
        
        # 接続テスト - clientsテーブルの件数を取得
        response = supabase.table('clients').select("count", count="exact").execute()
        print(f"✅ Connection successful!")
        print(f"Clients table count: {response.count}")
        
        # テーブル一覧の取得テスト
        tables = ['clients', 'profiles', 'job_requirements']
        for table in tables:
            try:
                response = supabase.table(table).select("*").limit(1).execute()
                print(f"✅ Table '{table}' accessible")
            except Exception as e:
                print(f"❌ Table '{table}' error: {e}")
                
    except Exception as e:
        print(f"❌ Connection failed: {e}")

if __name__ == "__main__":
    test_connection()
```

### 2. 実行方法

```bash
# 環境変数を設定
export SUPABASE_URL="https://xxxxxxxxxxxxx.supabase.co"
export SUPABASE_ANON_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# テスト実行
python test_supabase_connection.py
```

---

## 初期データの投入

### 1. 管理者プロファイルの作成

```sql
-- まず認証でユーザーを作成し、そのUIDを使用
-- Authentication → Users で手動ユーザー作成後、以下を実行

INSERT INTO profiles (id, full_name, role, department)
VALUES (
    'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx',  -- 実際のユーザーUIDに置き換え
    'システム管理者',
    'admin',
    'システム部'
);
```

### 2. テスト用クライアント企業の作成

```sql
INSERT INTO clients (name, industry, size, contact_person, contact_email, is_active)
VALUES 
    ('株式会社テストA', 'IT・通信', '100-500名', '採用担当 田中', 'recruit-tanaka@test-a.com', true),
    ('株式会社テストB', '製造業', '500-1000名', '人事部 佐藤', 'hr-sato@test-b.com', true),
    ('テストコンサルティング', 'コンサルティング', '50-100名', 'HR マネージャー', 'hr@test-consulting.com', true);
```

### 3. サンプル採用要件の作成

```sql
INSERT INTO job_requirements (client_id, title, description, structured_data, created_by)
VALUES (
    (SELECT id FROM clients WHERE name = '株式会社テストA' LIMIT 1),
    'Pythonエンジニア（フルスタック）',
    'Webアプリケーションの開発・保守を担当していただきます。Python/Django、React等の経験者歓迎。',
    '{
        "position": "フルスタックエンジニア",
        "required_skills": ["Python", "Django", "JavaScript"],
        "preferred_skills": ["React", "AWS", "Docker"],
        "experience_years": 3,
        "employment_type": "正社員",
        "salary_range": {"min": 500, "max": 800, "currency": "万円"}
    }'::jsonb,
    (SELECT id FROM profiles WHERE role = 'admin' LIMIT 1)
);
```

---

## バックアップ設定

### 1. 自動バックアップの確認

Supabaseでは以下の自動バックアップが提供されます：

```
Freeプラン:
- 自動バックアップ: 7日間
- ポイントインタイムリカバリ: なし

Proプラン:
- 自動バックアップ: 30日間
- ポイントインタイムリカバリ: 7日間
```

### 2. 手動バックアップの実行

```bash
# pg_dumpを使用した手動バックアップ
pg_dump "postgresql://postgres:[PASSWORD]@db.[PROJECT_ID].supabase.co:5432/postgres" > backup_$(date +%Y%m%d_%H%M%S).sql
```

### 3. バックアップスクリプトの自動化

```bash
#!/bin/bash
# backup_supabase.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="./backups"
PROJECT_ID="your-project-id"
PASSWORD="your-database-password"

mkdir -p $BACKUP_DIR

pg_dump "postgresql://postgres:$PASSWORD@db.$PROJECT_ID.supabase.co:5432/postgres" \
    --no-owner --no-privileges \
    > "$BACKUP_DIR/supabase_backup_$DATE.sql"

echo "Backup completed: $BACKUP_DIR/supabase_backup_$DATE.sql"

# 30日以上古いバックアップを削除
find $BACKUP_DIR -name "supabase_backup_*.sql" -mtime +30 -delete
```

---

## 監視とメンテナンス

### 1. データベースの監視

Supabaseダッシュボードで以下を定期的に確認：

```
- Database size
- Connection count
- Query performance
- Error logs
```

### 2. 定期メンテナンス

月次で以下を実行することを推奨：

```sql
-- データベース統計の更新
ANALYZE;

-- 不要データの削除
DELETE FROM retry_queue 
WHERE status = 'completed' 
  AND created_at < NOW() - INTERVAL '30 days';

-- ログテーブルのクリーンアップ
DELETE FROM job_status_history 
WHERE created_at < NOW() - INTERVAL '90 days';
```

### 3. パフォーマンス監視

```sql
-- 遅いクエリの確認
SELECT query, mean_time, calls
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;

-- テーブルサイズの確認
SELECT 
    schemaname,
    tablename,
    attname,
    n_distinct,
    correlation
FROM pg_stats
WHERE schemaname = 'public'
ORDER BY tablename, attname;
```

---

## トラブルシューティング

### よくある問題と解決方法

#### 1. 接続エラー
```
Error: Invalid API key
```
**解決方法:** APIキーの再確認、環境変数の設定確認

#### 2. RLSエラー
```
Error: new row violates row-level security policy
```
**解決方法:** ポリシーの確認、サービスロールキーの使用

#### 3. パフォーマンス問題
**解決方法:** インデックスの追加、クエリの最適化

詳細なトラブルシューティングは[トラブルシューティングガイド](../operations/troubleshooting.md)を参照してください。

---

## 次のステップ

Supabaseのセットアップが完了したら：

1. [BigQueryセットアップ](bigquery.md) - 大規模データ用DB設定
2. [環境設定](environment.md) - 他の環境変数設定
3. [API仕様書](../api/reference.md) - FastAPI開発

## 参考リンク

- [Supabase公式ドキュメント](https://supabase.com/docs)
- [PostgreSQL公式ドキュメント](https://www.postgresql.org/docs/)
- [Row Level Security ガイド](https://supabase.com/docs/guides/auth/row-level-security)