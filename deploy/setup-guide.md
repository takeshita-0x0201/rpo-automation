# RPO Automation デプロイガイド（Supabase + Render）

## 1. Supabase セットアップ

### 1.1 アカウント作成
1. [Supabase](https://supabase.com)にアクセス
2. GitHubアカウントでサインアップ（推奨）
3. 新規プロジェクトを作成
   - Project Name: `rpo-automation`
   - Database Password: 強力なパスワードを生成
   - Region: `Northeast Asia (Tokyo)`を選択

### 1.2 データベース設定
1. プロジェクトダッシュボードから「SQL Editor」を開く
2. 以下のSQLを実行してテーブルを作成：

```sql
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    is_admin BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Clients table
CREATE TABLE clients (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Requirements table
CREATE TABLE requirements (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    target_count INTEGER,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Scraping sessions table
CREATE TABLE scraping_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    client_id UUID REFERENCES clients(id),
    requirement_id UUID REFERENCES requirements(id),
    status VARCHAR(50) DEFAULT 'active',
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP WITH TIME ZONE
);

-- Candidates table
CREATE TABLE candidates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES scraping_sessions(id),
    client_id UUID REFERENCES clients(id),
    requirement_id UUID REFERENCES requirements(id),
    candidate_id VARCHAR(255),
    candidate_link TEXT,
    candidate_company VARCHAR(255),
    candidate_resume TEXT,
    age INTEGER,
    gender VARCHAR(10),
    enrolled_company_count INTEGER,
    platform VARCHAR(50),
    scraped_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX idx_candidates_session_id ON candidates(session_id);
CREATE INDEX idx_candidates_client_id ON candidates(client_id);
CREATE INDEX idx_candidates_requirement_id ON candidates(requirement_id);
CREATE INDEX idx_scraping_sessions_user_id ON scraping_sessions(user_id);
```

### 1.3 接続情報の取得
1. Settings → Database を開く
2. 以下の情報をコピー：
   - `Connection string` (DATABASE_URL)
   - `Host`
   - `Password`
3. Settings → API を開く
4. 以下の情報をコピー：
   - `URL` (SUPABASE_URL)
   - `anon public` key (SUPABASE_ANON_KEY)
   - `service_role` key (SUPABASE_SERVICE_KEY) ※秘密にすること

## 2. Render セットアップ

### 2.1 アカウント作成
1. [Render](https://render.com)にアクセス
2. GitHubアカウントでサインアップ

### 2.2 GitHubリポジトリの準備
1. RPO AutomationプロジェクトをGitHubにプッシュ
2. `render.yaml`と`requirements-render.txt`が含まれていることを確認

### 2.3 Renderでのデプロイ
1. Renderダッシュボードで「New +」→「Web Service」をクリック
2. GitHubリポジトリを接続
3. 以下の設定を行う：

#### 基本設定
- **Name**: `rpo-automation-api`
- **Environment**: `Python`
- **Build Command**: `pip install -r requirements-render.txt`
- **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`

#### 環境変数の設定
「Environment」タブで以下の環境変数を追加：

```bash
DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-ID].supabase.co:5432/postgres
SUPABASE_URL=https://[YOUR-PROJECT-ID].supabase.co
SUPABASE_ANON_KEY=[YOUR-ANON-KEY]
SUPABASE_SERVICE_KEY=[YOUR-SERVICE-KEY]
JWT_SECRET_KEY=[GENERATE-RANDOM-KEY]
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
ENVIRONMENT=production
CHROME_EXTENSION_ID=[YOUR-EXTENSION-ID]
CORS_ORIGINS=chrome-extension://[YOUR-EXTENSION-ID]
```

**JWT_SECRET_KEY の生成方法**:
```python
import secrets
print(secrets.token_urlsafe(32))
```

### 2.4 デプロイの実行
1. 「Create Web Service」をクリック
2. デプロイが自動的に開始される
3. ログを確認して正常に起動したことを確認

## 3. Chrome拡張機能の設定更新

### 3.1 API URLの更新
`extension/background/service-worker.js`を編集：

```javascript
// API ベースURL取得
function getApiBaseUrl() {
  // 本番環境
  return 'https://rpo-automation-api.onrender.com';
  // 開発環境では以下に切り替え
  // return 'http://localhost:8000';
}
```

### 3.2 manifest.jsonの更新
`extension/manifest.json`の`host_permissions`にRenderのURLを追加：

```json
"host_permissions": [
  "https://*.bizreach.jp/*",
  "https://*.openwork.jp/*",
  "https://*.rikunabi.com/*",
  "http://localhost:8000/*",
  "https://rpo-automation-api.onrender.com/*"
]
```

### 3.3 拡張機能の再インストール
1. Chrome拡張機能管理ページで既存の拡張機能を削除
2. 更新したコードで再度「パッケージ化されていない拡張機能を読み込む」
3. 新しい拡張機能IDをコピー
4. RenderとSupabaseの環境変数を更新

## 4. 動作確認

### 4.1 APIエンドポイントの確認
ブラウザで以下にアクセス：
- `https://rpo-automation-api.onrender.com/docs` - Swagger UI
- `https://rpo-automation-api.onrender.com/health` - ヘルスチェック

### 4.2 拡張機能の動作確認
1. 拡張機能のポップアップを開く
2. ログイン機能をテスト
3. スクレイピング機能をテスト

## 5. トラブルシューティング

### CORS エラーが発生する場合
- Renderの環境変数`CORS_ORIGINS`に正しい拡張機能IDが設定されているか確認
- 拡張機能IDは`chrome://extensions/`で確認可能

### データベース接続エラー
- SupabaseのConnection Poolingを有効にする
- DATABASE_URLの末尾に`?pgbouncer=true`を追加

### デプロイが失敗する場合
- Renderのログを確認
- Pythonバージョンを明示的に指定（`PYTHON_VERSION=3.9`）

## 6. 無料枠の制限

### Render
- 750時間/月の無料実行時間
- 15分間アクセスがないとスリープ（初回アクセス時に起動）
- 100GB/月の帯域幅

### Supabase
- 500MBのデータベースストレージ
- 2GBの帯域幅
- 50,000行の読み取り/月

本番運用では必要に応じて有料プランへの移行を検討してください。