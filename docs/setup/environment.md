# 環境設定ガイド

## 前提条件

以下の項目が設定されていることを確認してください：

- Python 3.9以上
- GCPアカウント
- Google Workspace
- Bizreachアカウント
- Google Chrome
- Git

## 開発環境のセットアップ

### 1. リポジトリのクローンと基本設定

```bash
# リポジトリのクローン
git clone https://github.com/[your-org]/rpo-automation.git
cd rpo-automation

# 仮想環境の作成
python -m venv venv

# 仮想環境の有効化
# Linux/Mac:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# 依存関係のインストール
pip install -r requirements.txt
```

### 2. GCPプロジェクトの設定

```bash
# gcloud CLIのインストール（未インストールの場合）
# https://cloud.google.com/sdk/docs/install を参照

# gcloudの初期化
gcloud init

# プロジェクトの設定
gcloud config set project [YOUR_PROJECT_ID]

# 認証
gcloud auth login
gcloud auth application-default login
```

### 3. 必要なGCP APIの有効化

```bash
# 必要なAPIを一括有効化
gcloud services enable \
    bigquery.googleapis.com \
    cloudfunctions.googleapis.com \
    run.googleapis.com \
    secretmanager.googleapis.com \
    cloudresourcemanager.googleapis.com \
    sheets.googleapis.com
```

### 4. サービスアカウントの作成

```bash
# BigQuery用サービスアカウント
gcloud iam service-accounts create rpo-automation-bigquery \
    --display-name="RPO Automation BigQuery Service Account"

# 必要な権限を付与
gcloud projects add-iam-policy-binding [YOUR_PROJECT_ID] \
    --member="serviceAccount:rpo-automation-bigquery@[YOUR_PROJECT_ID].iam.gserviceaccount.com" \
    --role="roles/bigquery.dataEditor"

gcloud projects add-iam-policy-binding [YOUR_PROJECT_ID] \
    --member="serviceAccount:rpo-automation-bigquery@[YOUR_PROJECT_ID].iam.gserviceaccount.com" \
    --role="roles/bigquery.jobUser"

# キーファイルの作成
gcloud iam service-accounts keys create ./credentials/bigquery-service-account.json \
    --iam-account=rpo-automation-bigquery@[YOUR_PROJECT_ID].iam.gserviceaccount.com
```

### 5. 環境変数の設定

```bash
# .env.exampleをコピー
cp .env.example .env
```

`.env`ファイルを編集し、以下の値を設定：

```bash
# GCP設定
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=./credentials/bigquery-service-account.json
BIGQUERY_DATASET=recruitment_data

# Supabase設定（後で設定）
SUPABASE_URL=https://xxxxxxxxxxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJS...
SUPABASE_SERVICE_KEY=eyJhbGciOiJS...

# API Keys（後で設定）
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...

# FastAPI設定
SECRET_KEY=your-secret-key-here
CORS_ORIGINS=http://localhost:3000,chrome-extension://[EXTENSION_ID]

# Google Sheets設定（後で設定）
GOOGLE_SHEETS_ID=your-sheets-id
```

### 6. ディレクトリ構造の作成

```bash
# 必要なディレクトリを作成
mkdir -p credentials logs temp
```

### 7. 開発用WebAppの起動テスト

```bash
# WebAppディレクトリに移動
cd src/web

# FastAPIサーバーの起動
uvicorn main:app --reload --port 8000
```

ブラウザで `http://localhost:8000` にアクセスし、「Hello World」が表示されることを確認してください。

## 環境別設定

### 開発環境（ローカル）

開発環境では以下の設定を使用：

```bash
# .env.development
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG

# ローカルデータベース設定
BIGQUERY_DATASET=recruitment_data_dev
```

### ステージング環境

```bash
# .env.staging
ENVIRONMENT=staging
DEBUG=false
LOG_LEVEL=INFO

# ステージング用データセット
BIGQUERY_DATASET=recruitment_data_staging
```

### 本番環境

```bash
# .env.production
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=WARNING

# 本番用データセット
BIGQUERY_DATASET=recruitment_data_prod
```

## セキュリティのベストプラクティス

### 1. 認証情報の管理

- `.env`ファイルをGitにコミットしない（`.gitignore`に追加済み）
- 本番環境ではSecret Managerを使用
- サービスアカウントキーの定期的なローテーション

### 2. 最小権限の原則

各サービスアカウントには必要最小限の権限のみを付与：

```bash
# BigQuery用（読み書き）
roles/bigquery.dataEditor
roles/bigquery.jobUser

# Cloud Functions用（実行）
roles/cloudfunctions.invoker

# Cloud Run用（デプロイ）
roles/run.developer
```

### 3. ネットワークセキュリティ

- 開発環境でも可能な限りHTTPS使用
- Chrome拡張機能のOrigin制限
- CORS設定の適切な管理

## トラブルシューティング

### よくある問題と解決方法

#### 1. Python仮想環境が有効化されない

```bash
# Windows PowerShellの場合
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

#### 2. gcloud認証エラー

```bash
# 認証をリセット
gcloud auth revoke --all
gcloud auth login
gcloud auth application-default login
```

#### 3. BigQuery権限エラー

```bash
# サービスアカウントの権限を確認
gcloud projects get-iam-policy [YOUR_PROJECT_ID] \
    --flatten="bindings[].members" \
    --format="table(bindings.role)" \
    --filter="bindings.members:rpo-automation-bigquery@[YOUR_PROJECT_ID].iam.gserviceaccount.com"
```

#### 4. 依存関係のインストールエラー

```bash
# pipのアップグレード
pip install --upgrade pip

# 個別インストール
pip install -r requirements.txt --no-cache-dir
```

## 次のステップ

環境設定が完了したら、以下のドキュメントに進んでください：

1. [Supabaseセットアップ](supabase.md) - Supabaseプロジェクトの設定
2. [BigQueryセットアップ](bigquery.md) - BigQueryプロジェクトの設定
3. [Chrome拡張機能セットアップ](chrome-extension.md) - 拡張機能の開発環境設定

## 環境設定チェックリスト

- [ ] Python 3.9以上がインストール済み
- [ ] 仮想環境が作成・有効化済み
- [ ] 依存関係がインストール済み
- [ ] GCPプロジェクトが設定済み
- [ ] 必要なAPIが有効化済み
- [ ] サービスアカウントが作成済み
- [ ] 環境変数が設定済み
- [ ] FastAPIがローカルで起動可能
- [ ] `.env`ファイルが`.gitignore`に含まれている