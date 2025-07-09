# セットアップガイド

## 前提条件

- Python 3.9以上
- GCPアカウント
- Google Workspace
- Bizreachアカウント
- Google Chrome

## インストール

### 1. リポジトリのクローン

```bash
# リポジトリのクローン
git clone https://github.com/[your-org]/rpo-automation.git
cd rpo-automation

# 仮想環境の作成
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 依存関係のインストール
pip install -r requirements.txt
```

### 2. Chrome拡張機能のセットアップ

#### 拡張機能のビルド
```bash
# 拡張機能をビルド
python scripts/build_extension.py

# または手動でファイルをコピー
cp -r src/extension/ dist/extension/
```

#### 開発者モードでの読み込み
1. Chromeで `chrome://extensions/` を開く
2. 右上の「デベロッパーモード」をONにする
3. 「パッケージ化されていない拡張機能を読み込む」をクリック
4. `dist/extension/` フォルダを選択

#### 拡張機能の設定
1. 拡張機能のオプションページを開く
2. FastAPIのエンドポイントURLを設定
   - 開発環境: `http://localhost:8000`
   - 本番環境: `https://your-api.run.app`

## Supabaseプロジェクトのセットアップ

### 1. Supabaseアカウントの作成
1. [Supabase](https://supabase.com)にアクセス
2. GitHubアカウントまたはメールでサインアップ
3. 新規プロジェクトを作成
   - プロジェクト名: `rpo-automation`
   - データベースパスワード: 安全なパスワードを設定（後で使用）
   - リージョン: `Northeast Asia (Tokyo)` を推奨
   - 料金プラン: Free tier（開発・テスト用）

### 2. プロジェクト情報の取得
プロジェクトダッシュボードから以下の情報を取得：
- **Project URL**: `https://xxxxxxxxxxxxx.supabase.co`
- **Anon key**: `eyJhbGciOiJS...`（公開可能）
- **Service key**: `eyJhbGciOiJS...`（秘密、サーバー側のみ）

これらの値を`.env`ファイルに設定：
```bash
SUPABASE_URL=https://xxxxxxxxxxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJS...
SUPABASE_SERVICE_KEY=eyJhbGciOiJS...
```

### 3. データベーススキーマの作成
1. Supabaseダッシュボードの「SQL Editor」を開く
2. 「New query」をクリック
3. 以下のSQLを実行してテーブルを作成：

```sql
-- migrations/001_initial_schema_extension.sql の内容をコピー＆ペースト
```

または、プロジェクトのSQLファイルを直接実行：
```bash
# Supabase CLIを使用する場合（要インストール）
supabase db push --db-url "postgresql://postgres:[PASSWORD]@db.[PROJECT_ID].supabase.co:5432/postgres"
```

### 4. 認証設定
1. Authentication → Settings で以下を確認：
   - Email認証が有効になっていること
   - サイトURL: `http://localhost:8000`（開発環境）
   - リダイレクトURL: `http://localhost:8000/auth/callback`

2. Authentication → Users でテストユーザーを作成：
   - Email: `admin@example.com`
   - Password: 任意のパスワード

### 5. 初期データの投入
SQL Editorで以下を実行し、管理者プロファイルを作成：

```sql
-- 管理者ユーザーのプロファイル作成（UIDは実際のユーザーIDに置き換え）
INSERT INTO profiles (id, full_name, role, department)
VALUES (
    'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx',  -- Auth → Users から取得
    'システム管理者',
    'admin',
    'システム部'
);

-- テスト用クライアント企業の作成
INSERT INTO clients (name, industry, size, contact_person, contact_email)
VALUES 
    ('株式会社テストA', 'IT', '100-500名', '採用担当A', 'recruit-a@example.com'),
    ('株式会社テストB', '製造業', '500-1000名', '採用担当B', 'recruit-b@example.com');
```

### 6. 接続テスト
Pythonで接続確認：

```python
from supabase import create_client, Client
import os
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_ANON_KEY")

supabase: Client = create_client(url, key)

# テスト: クライアント一覧を取得
response = supabase.table('clients').select("*").execute()
print(response.data)
```

## BigQueryプロジェクトのセットアップ

### 1. BigQuery APIの有効化
1. [GCPコンソール](https://console.cloud.google.com)にアクセス
2. 「APIとサービス」→「ライブラリ」
3. 「BigQuery API」を検索して有効化
4. 「Cloud Resource Manager API」も同様に有効化

### 2. データセットの作成
```bash
# gcloud CLIを使用する場合
gcloud config set project YOUR_PROJECT_ID

# データセットの作成
bq mk --location=asia-northeast1 --dataset recruitment_data
bq mk --location=asia-northeast1 --dataset client_learning  
bq mk --location=asia-northeast1 --dataset system_logs
```

または、GCPコンソールから：
1. BigQuery → 「データセットを作成」
2. データセットID: `recruitment_data`、`client_learning`、`system_logs`
3. データのロケーション: `asia-northeast1`（東京）

### 3. テーブルの作成
プロジェクトのマイグレーションファイルを使用：

```bash
# recruitment_dataデータセット
bq query --use_legacy_sql=false < migrations/002_requirements_tables.sql

# client_learningデータセット
bq query --use_legacy_sql=false < migrations/003_client_learning_tables.sql

# system_logsデータセット
bq query --use_legacy_sql=false < migrations/004_system_logs_tables.sql

# ストアドプロシージャとUDF
bq query --use_legacy_sql=false < migrations/005_bigquery_procedures.sql
```

### 4. サービスアカウントの作成
1. IAMと管理 → サービスアカウント → 「作成」
2. サービスアカウント名: `rpo-automation-bigquery`
3. 役割を付与:
   - BigQuery データ編集者
   - BigQuery ジョブユーザー
4. キーを作成（JSON形式）してダウンロード

### 5. 環境変数の設定
ダウンロードしたキーファイルのパスを環境変数に設定：

```bash
# .envファイル
GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/service-account-key.json
BIGQUERY_PROJECT_ID=your-project-id
BIGQUERY_DATASET=recruitment_data
```

### 6. 接続テスト
Pythonで接続確認：

```python
from google.cloud import bigquery
import os
from dotenv import load_dotenv

load_dotenv()

# クライアントの初期化
client = bigquery.Client(project=os.getenv("BIGQUERY_PROJECT_ID"))

# データセット一覧の取得
datasets = list(client.list_datasets())
print("Datasets in project:")
for dataset in datasets:
    print(f"  {dataset.dataset_id}")

# テーブル一覧の取得
dataset_ref = client.dataset("recruitment_data")
tables = list(client.list_tables(dataset_ref))
print(f"\nTables in recruitment_data:")
for table in tables:
    print(f"  {table.table_id}")
```

### 7. スケジュールドクエリの設定（オプション）
日次レポート生成などの定期処理を設定：

1. BigQueryコンソール → 「スケジュールドクエリ」
2. 「スケジュールドクエリを作成」
3. クエリ例：
```sql
CALL system_logs.archive_old_logs();
```
4. スケジュール: 毎日午前2時（JST）

## 環境変数の設定

### .envファイルの作成
プロジェクトルートに`.env`ファイルを作成し、以下の環境変数を設定：

```bash
# Supabase
SUPABASE_URL=https://xxxxxxxxxxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJS...
SUPABASE_SERVICE_KEY=eyJhbGciOiJS...

# Google Cloud
GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/service-account-key.json
BIGQUERY_PROJECT_ID=your-project-id
BIGQUERY_DATASET=recruitment_data

# OpenAI
OPENAI_API_KEY=sk-...

# Google Gemini
GEMINI_API_KEY=AIza...

# Google Sheets
GOOGLE_SHEETS_SPREADSHEET_ID=your-spreadsheet-id

# FastAPI
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

## WebAppの起動

### 開発環境での起動
```bash
# FastAPIサーバーの起動
uvicorn src.web.main:app --reload --host 0.0.0.0 --port 8000

# または、起動スクリプトを使用
./run_webapp.sh
```

ブラウザで `http://localhost:8000` にアクセスして動作確認。

### 本番環境へのデプロイ
Cloud Runへのデプロイ手順は、[デプロイガイド](docs/DEPLOYMENT.md)を参照してください。

## トラブルシューティング

### よくある問題と解決方法

#### 1. Supabase接続エラー
- 環境変数が正しく設定されているか確認
- Supabaseプロジェクトがアクティブか確認
- ネットワーク接続を確認

#### 2. BigQuery権限エラー
- サービスアカウントに適切な権限が付与されているか確認
- 環境変数 `GOOGLE_APPLICATION_CREDENTIALS` が正しいパスを指しているか確認

#### 3. Chrome拡張機能が動作しない
- 開発者モードが有効になっているか確認
- コンソールログでエラーを確認
- FastAPIサーバーが起動しているか確認

詳細なトラブルシューティング情報は[トラブルシューティングガイド](docs/troubleshooting.md)を参照してください。