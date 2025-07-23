# RPO Automation System

採用代行業務を自動化・効率化する統合システム

## 概要

RPO（Recruitment Process Outsourcing）Automation Systemは、採用プロセス全体を効率化するための統合プラットフォームです。AIを活用した候補者マッチング、自動データ収集、クライアント評価管理など、採用業務に必要な機能を包括的に提供します。

### 主な特徴

- 🤖 **AIマッチング**: Google Gemini APIを活用した高精度な候補者マッチング
- 🌐 **自動データ収集**: Chrome拡張機能による求人サイトからの候補者情報自動収集
- 📊 **データ分析**: Supabaseを活用したリアルタイムデータ管理
- 🔄 **ベクトル検索**: Pineconeを使用した類似案件検索
- 📋 **クライアント評価**: Google Sheetsとの連携による評価データ管理

## プロジェクト構造

```
rpo-automation/
├── webapp/                    # FastAPI Webアプリケーション
│   ├── main.py               # アプリケーションエントリーポイント
│   ├── routers/              # APIルーター（認証、候補者、要件管理など）
│   ├── services/             # ビジネスロジック
│   ├── templates/            # HTMLテンプレート（管理画面）
│   └── static/               # CSS、JavaScript、画像
│
├── core/                      # 共通コアモジュール
│   ├── ai/                   # AI関連（Geminiクライアント）
│   ├── scraping/             # スクレイピング処理
│   ├── services/             # 共通サービス
│   └── utils/                # ユーティリティ
│
├── ai_matching_system/        # AIマッチングシステム
│   ├── ai_matching/          # マッチングロジック
│   └── scripts/              # データ処理スクリプト
│
├── extension/                 # Chrome拡張機能
│   ├── manifest.json         # 拡張機能設定
│   ├── background/           # バックグラウンド処理
│   ├── content/              # コンテンツスクリプト
│   └── popup/                # ポップアップUI
│
├── supabase/                  # Supabase Edge Functions
│   └── functions/
│       ├── vector-sync/      # ベクトルDB同期
│       └── process-matching/ # マッチング処理
│
├── database/                  # データベース関連
│   ├── migrations/           # マイグレーションスクリプト
│   ├── scripts/              # ユーティリティSQL
│   └── fixes/                # 修正スクリプト
│
├── scripts/                   # 運用・管理スクリプト
│   ├── setup/                # セットアップスクリプト
│   ├── processing/           # データ処理
│   └── utilities/            # ユーティリティ
│
├── tests/                     # テストファイル
├── data/                      # データファイル
└── docs/                      # ドキュメント
```

## クイックスタート

### 前提条件

- Python 3.8以上
- Node.js 14以上（Chrome拡張機能用）
- Supabaseアカウント
- Google Cloud Platform アカウント（Gemini API用）

### 1. リポジトリのクローン

```bash
git clone https://github.com/your-org/rpo-automation.git
cd rpo-automation
```

### 2. Python環境のセットアップ

```bash
# 仮想環境の作成
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 依存関係のインストール
pip install -r requirements.txt
```

### 3. 環境変数の設定

```bash
cp .env.example .env
```

`.env`ファイルを編集して以下の必須環境変数を設定：

```
# Supabase
SUPABASE_URL=your-supabase-url
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-key

# Google Gemini
GEMINI_API_KEY=your-gemini-api-key

# Pinecone (オプション)
PINECONE_API_KEY=your-pinecone-key
PINECONE_INDEX_HOST=your-index-host

# アプリケーション設定
JWT_SECRET_KEY=your-secret-key
GAS_API_KEY=your-gas-api-key
```

### 4. データベースのセットアップ

```bash
# Supabaseのダッシュボードで以下のSQLを実行
# 1. 初期スキーマ
database/migrations/001_initial_schema.sql

# 2. その他の必要なマイグレーション
database/migrations/配下のファイルを順番に実行
```

### 5. Webアプリケーションの起動

```bash
# プロジェクトルートから
./start_webapp.sh
```

アプリケーションは http://localhost:8000 でアクセスできます。

### 6. Chrome拡張機能のインストール

1. Chromeの拡張機能管理ページを開く（chrome://extensions/）
2. 「デベロッパーモード」を有効化
3. 「パッケージ化されていない拡張機能を読み込む」をクリック
4. `extension/`フォルダを選択

## 各機能の概要

### 1. Web管理画面

FastAPIベースの管理画面で、以下の機能を提供：

- **ユーザー管理**: 管理者、マネージャー、一般ユーザーの3つのロール
- **クライアント管理**: クライアント企業の情報管理
- **採用要件管理**: 求人要件の登録と管理
- **ジョブ管理**: スクレイピングとマッチングジョブの実行・監視
- **媒体管理**: 対応する求人サイトの設定

### 2. AIマッチングシステム

Google Gemini APIを使用した高度なマッチング機能：

- **自動評価**: 候補者と求人要件の適合度を4段階（A/B/C/D）で評価
- **詳細分析**: 必須要件ごとの充足度を個別に評価
- **レポート生成**: マッチング理由と推奨事項を含む詳細レポート

### 3. Chrome拡張機能

求人サイトからの候補者情報を自動収集：

- **対応サイト**: ビズリーチ（他サイトも拡張可能）
- **自動収集**: 候補者リストページから情報を自動抽出
- **バックグラウンド同期**: 収集したデータを自動的にサーバーへ送信

### 4. ベクトル検索システム

Pineconeを使用した類似案件検索：

- **自動ベクトル化**: Gemini Embeddingによるテキストのベクトル化
- **類似検索**: 過去の評価データから類似案件を検索
- **Edge Function**: 1時間ごとの自動同期処理

### 5. Google Sheets連携

クライアント評価データの管理：

- **GAS連携**: Google Apps Scriptによる自動データ同期
- **バッチアップロード**: 評価データの一括登録
- **双方向同期**: スプレッドシートとデータベースの同期

## 開発者向け情報

### ディレクトリ構成の詳細

- `webapp/`: メインのWebアプリケーション（FastAPI）
- `core/`: 共通で使用されるコアモジュール
- `extension/`: Chrome拡張機能のソースコード
- `supabase/functions/`: Edge Functionsのソースコード
- `database/`: データベース関連のSQLファイル
- `scripts/`: 運用・管理用のPythonスクリプト
- `tests/`: テストコード
- `docs/`: プロジェクトドキュメント

### 主要な技術スタック

- **Backend**: FastAPI, Python 3.8+
- **Database**: Supabase (PostgreSQL)
- **AI/ML**: Google Gemini API, Pinecone
- **Frontend**: Jinja2 Templates, Bootstrap 5
- **Extension**: Chrome Extension API, JavaScript
- **Cloud Functions**: Supabase Edge Functions (Deno)

### コーディング規約

- Python: PEP 8に準拠
- JavaScript: ESLint設定に従う
- SQL: 小文字のsnake_caseを使用
- Git: Conventional Commitsを推奨

## ライセンス

本プロジェクトは[MITライセンス](LICENSE)の下で公開されています。

## サポート

問題や質問がある場合は、GitHubのIssueを作成してください。

---

最終更新日: 2025年7月23日