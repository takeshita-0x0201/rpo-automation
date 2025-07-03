# RPO自動化システム

AI・RPAツールを活用した採用代行業務（RPO）の自動化・効率化システム

## 概要

本システムは、RPO事業者がクライアント企業に代わってBizreachでの候補者スクリーニングから、AIによる採用要件マッチング判定、結果のレポーティングまでを自動化し、RPO業務の効率化を実現します。

### システム利用者
- **メインユーザー**: RPO事業者のスタッフのみ
- **クライアント企業**: 採用要件を提供し、結果を受け取る（システムに直接アクセスしない）

## エンタープライズ向けアーキテクチャ

### システム構成の課題と解決策

本システムは、セキュリティ上の制約により、Bizreachへのアクセスが貸与PCからのみ可能という環境で動作します。この制約を考慮し、**エージェント型アーキテクチャ**を採用し、ユーザビリティ向上のため**採用要件管理部分のみWebApp化**しています。

### WebApp化の範囲

#### WebApp化する機能（ユーザーインターフェース）
- **採用要件管理**: Bizreach風フォームでの要件登録・編集
- **実行管理**: スクレイピング実行指示と状況モニタリング  
- **結果確認**: 処理完了通知とGoogle Sheetsへのリンク

#### バックエンド処理（WebApp化しない）
- **スクレイピング**: 貸与PCエージェントで実行
- **AI判定**: Cloud Functionsでバックグラウンド処理
- **データ出力**: 自動的にGoogle Sheets/BigQueryへ保存

```mermaid
graph TD
    subgraph "ユーザーインターフェース"
        A[RPOスタッフ]
        B[WebApp<br/>Cloud Run]
    end
    
    subgraph "クラウド環境 (GCP)"
        C[Cloud Functions<br/>制御系]
        D[Pub/Sub<br/>メッセージキュー]
        E[BigQuery<br/>データ保存]
        F[Gemini API]
        G[ChatGPT-4o API]
    end
    
    subgraph "実行環境"
        H[貸与PC<br/>エージェント]
        I[Bizreach]
    end
    
    subgraph "結果確認"
        J[Google Sheets]
    end
    
    A -->|要件登録・実行指示| B
    B -->|API呼び出し| C
    C -->|ジョブ送信| D
    D -->|ポーリング| H
    H -->|スクレイピング| I
    H -->|結果送信| D
    D -->|データ取得| C
    C -->|構造化依頼| F
    C -->|判定依頼| G
    C -->|保存| E
    C -->|出力| J
    B -->|結果表示| A
    J -->|確認| A
```

### エージェント型アーキテクチャの特徴

1. **非同期通信**: Google Cloud Pub/Subを使用し、貸与PCとクラウド間で非同期にメッセージをやり取り
2. **疎結合**: 各コンポーネントが独立して動作し、障害の影響範囲を限定
3. **スケーラブル**: 複数の貸与PCエージェントを並列実行可能

## WebAppの役割と機能

### WebAppの主要機能

#### 1. 採用要件管理（CRUD操作）
- **新規登録**: Bizreach風フォームで要件を入力
- **一覧表示**: 登録済み要件の確認と管理
- **編集・削除**: 既存要件の更新と削除

#### 2. 実行管理
- **ジョブ実行**: スクレイピング実行の指示
- **状況モニタリング**: リアルタイムでの進捗表示
- **エラー通知**: 失敗時の詳細情報表示

#### 3. 結果確認
- **完了通知**: 処理完了の表示
- **統計表示**: 候補者数、マッチ率など
- **詳細リンク**: Google Sheetsへの直接アクセス

#### 4. ユーザー管理
- **認証**: RPOスタッフのログイン機能
- **権限管理**: スタッフの役職別アクセス制御

### WebAppが担当しない機能
- **Pub/Subポーリング**: 貸与PCエージェントが実行
- **直接的なBigQuery操作**: Cloud Functions経由で実行
- **スクレイピング**: 貸与PCエージェントが実行

## システム全体のワークフロー

### Phase 1: 採用要件の登録

```mermaid
graph TD
    A[RPOスタッフ] -->|1: 要件作成| B{入力方法選択}
    B -->|簡易版| C[Bizreach風フォーム]
    B -->|詳細版| D[自然言語で記述]
    
    C -->|2: フォーム入力| E[構造化データ]
    D -->|2: テキスト入力| F[Gemini API]
    F -->|3: AI構造化| E
    
    E -->|4: 確認画面| G[RPOスタッフが確認・修正]
    G -->|5: 登録完了| H[(BigQuery保存)]
```

**特徴的な機能:**
- **Bizreach検索UIとの統一**: 採用要件入力フォームをBizreachの検索画面と同じUIで実装
- **AI自動構造化**: 自然言語で書かれた要件をGemini APIが自動でJSON構造化

### Phase 2: 候補者検索の実行

1. RPOスタッフが登録済み要件から選択
2. Cloud FunctionsがPub/Sub経由でジョブを送信
3. 貸与PCエージェントが定期的にポーリング
4. Bizreachで自動検索・データ取得
5. 結果をPub/Sub経由でクラウドに送信

### Phase 3: AI判定とレポート生成

1. 取得した候補者データをChatGPT-4oでマッチング判定
2. スコア・評価理由を含むレポートを自動生成
3. Google Sheetsに結果を自動出力
4. RPOスタッフに完了通知

### Phase 4: フィードバックと継続的改善

RPOスタッフからのフィードバックとクライアント企業からの採用結果を蓄積し、AI判定の精度を継続的に向上させます。

## 処理の詳細フロー

### 採用要件登録からスクレイピング実行まで

```mermaid
sequenceDiagram
    participant User as 採用担当者
    participant WebApp as WebApp
    participant CF as Cloud Functions
    participant BQ as BigQuery
    participant PS as Pub/Sub
    participant Agent as 貸与PCエージェント
    
    User->>WebApp: 1. 採用要件を登録
    WebApp->>CF: 2. 要件データ送信
    CF->>BQ: 3. 要件を保存
    Note over BQ: requirement_id生成
    
    User->>WebApp: 4. "スクレイピング実行"ボタン
    WebApp->>CF: 5. requirement_idで実行指示
    CF->>BQ: 6. 要件データ取得
    CF->>PS: 7. ジョブメッセージ投稿
    
    Agent->>PS: 8. ポーリング
    PS->>Agent: 9. ジョブ受信
    Agent->>Agent: 10. スクレイピング実行
    Agent->>PS: 11. 候補者データ送信
    
    PS->>CF: 12. 結果を送信
    CF->>CF: 13. AI判定実行
    CF->>BQ: 14. 結果保存
```

## クラウドアーキテクチャ (GCP)

本システムは、サーバーレスアーキテクチャを全面的に採用しており、インフラの管理コストを最小限に抑えています。

- **Cloud Run:**
  - **役割:** WebAppのホスティング。FastAPIアプリケーションをコンテナとして実行し、ユーザーインターフェースを提供します。
  - **特徴:** オートスケーリング、ゼロスケール対応、HTTPS自動化

- **Cloud Functions:**
  - **役割:** バックエンド処理の実行。WebAppからのAPIリクエストを受けて、BigQuery操作、Pub/Subメッセージ送信、AI判定等を実行します。
  - **トリガー:** HTTPリクエスト、Pub/Subメッセージ、Cloud Scheduler

- **BigQuery:**
  - **役割:** 大規模データウェアハウス。処理の過程で生成されるすべてのログ、候補者データ、AIの判定結果などを保存する「公式の記録保管庫」です。データの分析や、過去の判定傾向の確認などに利用します。

- **Secret Manager:**
  - **役割:** APIキーやデータベースのパスワードなど、機密情報を安全に保管・管理します。コード内に直接書き込むことを避け、セキュリティを向上させます。

- **Pub/Sub:**
  - **役割:** 非同期メッセージング。クラウドと貸与PCエージェント間の通信を仲介し、システムの疎結合を実現します。
  - **特徴:** メッセージの保管（最大7日間）、確実な配信保証

- **Identity and Access Management (IAM):**
  - **役割:** 各GCPサービスへのアクセス権限を管理します。例えば、「Cloud FunctionsはSecret Managerから秘密情報を読み取れるが、BigQueryのテーブルは削除できない」といった細かい権限設定を行い、最小権限の原則を徹底します。

- **Cloud Logging & Cloud Monitoring:**
  - **役割:** システムの監視を担当します。Cloud Loggingはプログラムの出力ログ（`print`や`logging`）をすべて集約し、エラーの追跡を容易にします。Cloud Monitoringは、エラーの発生回数や関数の実行時間などをグラフで可視化し、異常があればアラートを送信するように設定できます。

## 主な機能

### コア機能
- **WebAppによる簡単操作**: ブラウザから採用要件の登録・実行・確認が可能
- **自動スクリーニング**: Bizreachから候補者情報を自動取得
- **AI判定**: 採用要件との適合性をAIが判定・スコアリング
- **構造化データ管理**: 候補者情報・採用要件をJSON形式で管理
- **レポート生成**: Google Sheetsへの自動出力

### 差別化機能
- **Bizreach検索UIとの統一**: 使い慣れたUIで採用要件を入力
- **エージェント型アーキテクチャ**: セキュリティ制約に対応
- **クライアント別最適化**: クライアント企業毎の採用パターンを学習
- **完全自動化**: 要件登録から結果出力まで人手不要

## システムアーキテクチャ

### 技術スタック

- **言語**: Python 3.9+
- **インフラ**: Google Cloud Platform (GCP)
  - Cloud Run (WebApp)
  - Cloud Functions (バックエンド処理)
  - Pub/Sub (メッセージング)
  - BigQuery (データストア)
- **AI/ML**: 
  - Google Gemini (構造化・プロンプト生成)
  - OpenAI ChatGPT-4o (マッチング判定)
- **WebApp**:
  - FastAPI (バックエンドAPI)
  - Bootstrap (UI/UX)
- **ブラウザ自動化**: Playwright
- **連携**: Google Sheets API

### データフロー

1. **採用要件取得**: Webフォームまたは自然言語入力から要件を取得しJSON構造化
2. **候補者検索**: 貸与PCエージェントがBizreachで自動検索・情報取得
3. **AI判定**: 要件と候補者のマッチング判定（ChatGPT-4o）
4. **結果出力**: Google Sheetsへ結果を記録
5. **フィードバック**: 企業別の採用パターンを学習データとして蓄積

### データベース設計

本システムは2つのデータベースサービスを使い分けることで、パフォーマンスとコストの最適化を実現します。

#### 1. Supabase (PostgreSQL互換)
**目的**: WebAppのリアルタイム処理とトランザクション管理

**主要テーブル**:
- **ユーザー管理**
  - Supabase Auth利用（組み込み認証）
  - `profiles`: ユーザー拡張情報（企業ID、役職等）
  - `user_companies`: ユーザーと企業の紐付け

- **ジョブ実行管理**
  - `jobs`: 実行ジョブ（ID、要件ID、ステータス、作成日時）
  - `job_status`: 実行状況のリアルタイム更新
  - `retry_queue`: 失敗ジョブのリトライ管理

- **システム設定**
  - `company_settings`: 企業別の設定値
  - `notification_settings`: 通知設定

**運用方針**:
- 無料プラン（500MB、無制限API呼び出し）
- リアルタイム購読でステータス更新を即座に反映
- Row Level Security (RLS)で企業間のデータ分離
- 自動バックアップ（有料プランで利用可）

#### 2. BigQuery
**目的**: 大規模データの蓄積と分析

**主要データセット**:
- **採用データ** (`recruitment_data`)
  - `requirements`: 採用要件マスタ（原本テキスト、構造化JSON、企業ID）
  - `candidates`: 候補者情報（プロフィール、スキル、経歴）
  - `ai_evaluations`: AI判定結果（スコア、理由、判定日時）
  - `screening_sessions`: スクレイピング実行履歴

- **企業学習データ** (`company_learning`)
  - `company_patterns`: 企業別の採用パターン（用語定義、重視項目）
  - `successful_hires`: 採用成功事例
  - `feedback_history`: フィードバック履歴

- **システムログ** (`system_logs`)
  - `audit_logs`: 監査ログ（全操作履歴）
  - `api_access_logs`: APIアクセスログ
  - `performance_metrics`: パフォーマンス指標

**運用方針**:
- パーティション分割（日付別）でクエリコストを削減
- 90日以上前のデータは自動的にコールドストレージへ移行
- スケジュールドクエリで日次集計を自動化
- データポータルでダッシュボード作成

#### データベース連携
- Cloud SQLの実行完了ジョブは、バッチでBigQueryへ転送
- BigQueryの集計結果は、必要に応じてCloud SQLにキャッシュ
- マルチテナントは`company_id`による論理分離で実現

## プロジェクト構成（詳細）

プロジェクトの全体像を把握しやすくするため、各ディレクトリに含まれる主要なファイルとその役割を解説します。

```
rpo-automation/
│
├── src/                     # プログラムの心臓部。ビジネスロジックを格納。
│   │
│   ├── agent/               # 貸与PC上で動作するエージェント関連
│   │   ├── agent.py         # メインのエージェントプログラム
│   │   ├── poller.py        # Pub/Subからジョブを取得するポーリング処理
│   │   └── executor.py      # スクレイピング実行とエラーハンドリング
│   │
│   ├── scraping/            # Webサイトから情報を取得するスクレイピング関連
│   │   └── bizreach.py      # Bizreachのサイトを操作し、候補者情報を取得する
│   │
│   ├── ai/                  # AIモデルとの連携やプロンプト生成
│   │   ├── gemini_client.py # Google Gemini APIと通信するためのクライアント
│   │   ├── openai_client.py # OpenAI API(ChatGPT)と通信するためのクライアント
│   │   └── matching_engine.py # 採用要件と候補者情報を基に、AIにマッチング判定を依頼する
│   │
│   ├── data/                # データの変換や整形、構造化を担当
│   │   ├── structure.py     # 採用要件を構造化する
│   │   └── client_patterns.py  # クライアント企業別の採用パターンを管理
│   │
│   ├── web/                 # WebApp関連（FastAPI）
│   │   ├── main.py          # FastAPIアプリケーションのエントリーポイント
│   │   ├── routers/         # APIルーター
│   │   │   ├── requirements.py  # 採用要件管理API
│   │   │   ├── jobs.py          # ジョブ実行管理API
│   │   │   └── results.py       # 結果確認API
│   │   ├── models/          # Pydanticモデル
│   │   ├── templates/       # HTMLテンプレート
│   │   └── static/          # CSS/JS（Bootstrap）
│   │
│   ├── sheets/              # Google Sheetsとの連携
│   │   └── writer.py        # AIの判定結果をスプレッドシートに書き込む
│   │
│   └── utils/               # 複数の機能で共通して使われる便利機能
│       ├── logging_config.py  # ログの出力形式やレベルを設定する
│       └── env_loader.py      # .envファイルから環境変数を読み込む
│
├── config/                  # 設定ファイルを格納
│   └── settings.py          # プロジェクト全体で利用する定数や設定値（例: タイムアウト秒数）
│
├── tests/                   # プログラムの品質を保証するテストコード
│   ├── unit/                # 関数単位の小さなテスト
│   └── integration/         # 複数の機能を連携させた大きなテスト
│
├── docs/                    # プロジェクトの仕様や設計に関するドキュメント
│   └── troubleshooting.md   # よくある問題と解決策をまとめる
│
├── scripts/                 # プロジェクトのメイン処理を実行するスクリプト
│   ├── daily_screening.py   # 日次のスクリーニングタスク（データ取得→AI判定→出力）を実行する
│   └── install_agent.py     # 貸与PCにエージェントをインストールするスクリプト
│
├── .env.example             # 環境変数のテンプレートファイル
├── requirements.txt         # プロジェクトに必要なPythonライブラリの一覧
└── README.md                # このファイル。プロジェクトの全体像を説明
```

## セットアップ

### 前提条件

- Python 3.9以上
- GCPアカウント
- Google Workspace
- Bizreachアカウント

### インストール

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

### 環境設定

1. GCPプロジェクトの設定
```bash
gcloud init
gcloud config set project [YOUR_PROJECT_ID]
```

2. 環境変数の設定
```bash
cp .env.example .env
# .envファイルを編集して必要な情報を設定
```

### 必要な環境変数

#### WebApp環境（Cloud Run）
- `SUPABASE_URL`: SupabaseプロジェクトURL（例: `https://xxxxx.supabase.co`）
- `SUPABASE_ANON_KEY`: Supabase匿名キー（公開可能）
- `SUPABASE_SERVICE_KEY`: Supabaseサービスキー（管理者用、秘密）
- `CLOUD_FUNCTIONS_URL`: バックエンドAPIのURL
- `GOOGLE_CLOUD_PROJECT`: GCPプロジェクトID
- `SECRET_KEY`: FastAPI用のシークレットキー

#### クラウド環境（Cloud Functions）
- `GOOGLE_CLOUD_PROJECT`: GCPプロジェクトID
- `BIGQUERY_DATASET`: BigQueryデータセット名
- `OPENAI_API_KEY`: OpenAI APIキー
- `GEMINI_API_KEY`: Gemini APIキー
- `GOOGLE_SHEETS_ID`: 出力先のGoogle Sheets ID
- `PUBSUB_TOPIC`: Pub/Subトピック名
- `PUBSUB_SUBSCRIPTION`: Pub/Subサブスクリプション名

#### エージェント環境（貸与PC）
- `GOOGLE_CLOUD_PROJECT`: GCPプロジェクトID
- `PUBSUB_SUBSCRIPTION`: ジョブ受信用サブスクリプション
- `PUBSUB_RESULT_TOPIC`: 結果送信用トピック
- `BIZREACH_USERNAME`: Bizreachログイン用ユーザー名
- `BIZREACH_PASSWORD`: Bizreachログイン用パスワード

## 使用方法

### WebAppの起動

```bash
# 開発環境での起動
cd src/web
uvicorn main:app --reload --port 8000

# ブラウザでアクセス
# http://localhost:8000
```

### エージェントの起動（貸与PC）

```bash
# エージェントの実行
python src/agent/agent.py
```

### 手動実行（開発・デバッグ用）

```bash
# 採用要件の構造化テスト
python -m src.data.structure_requirements --text "Pythonエンジニア募集..."

# AI判定テスト
python -m src.ai.matching_engine --requirement-id [REQ_ID] --candidate-id [CAND_ID]
```

## WBS（作業計画書）

このセクションでは、本プロジェクトの開発タスクを詳細に分解したWBS（Work Breakdown Structure）を提示します。
文系出身の新卒エンジニアが一人でタスクを理解し、実装まで進められるように、各タスクの目的、具体的な作業内容、完了の定義、参考情報を記載しています。

### フェーズ1: 環境構築と基礎理解 (目標: 1週間)

**目的:** プロジェクトを自分のPCで動かすための準備を整え、基本的な仕組みを理解する。

| No. | タスク名 | 担当 | 状態 | 期限 | 成果物 | 詳細 |
| :-- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1.1 | **開発環境のセットアップ** | | 完了 | Day 1 | - | **目的:** Pythonコードを実行できる環境を整える。<br> **作業内容:**<br> - `README`の「前提条件」を確認し、Python 3.9以上がインストールされているか確認する (`python --version`)。<br> - `README`の「インストール」セクションに従い、リポジトリをクローンし、仮想環境(`venv`)を作成・有効化する。<br> - `pip install -r requirements.txt` を実行し、必要なライブラリをインストールする。<br> **完了の定義:** エラーなく`pip install`が完了し、`pip list`でライブラリが確認できること。 |
| 1.2 | **GCP/Google Workspaceのセットアップ** | | 完了 | Day 2 | - | **目的:** プロジェクトが連携するGoogleサービスを使えるようにする。<br> **作業内容:**<br> - `README`の「環境設定」に従い、`gcloud init`を実行し、手持ちのGCPプロジェクトと連携させる。<br> - Google Docs, Google Sheets APIを有効化する。<br> - サービスアカウントを作成し、キー（JSONファイル）をダウンロードする。<br> **完了の定義:** `gcloud config list`で自分のプロジェクトが表示されること。APIが有効化されていること。 |
| 1.3 | **環境変数の設定** | | 完了 | Day 3 | `.env`ファイル | **目的:** APIキーなどの秘密情報をコードから分離し、安全に管理する。<br> **作業内容:**<br> - `cp .env.example .env` を実行し、`.env`ファイルを作成する。<br> - `README`の「必要な環境変数」セクションを参考に、ダウンロードしたGCPのキー情報や、別途用意したOpenAI/GeminiのAPIキーなどを`.env`ファイルに書き込む。<br> **完了の定義:** 全ての必須環境変数が`.env`ファイルに設定されていること。 |
| 1.4 | **プロジェクト構成の理解** | | 完了 | Day 4 | - | **目的:** どこに何のコードがあるか把握する。<br> **作業内容:**<br> - `README`の「プロジェクト構成」を見る。<br> - `src`ディレクトリ内の各サブディレクトリ（`scraping`, `ai`, `data`, `sheets`, `utils`）の役割を推測する。<br> - 各ディレクトリ内のPythonファイル名を眺め、何をするためのファイルか想像してみる。<br> **完了の定義:** 各ディレクトリの役割を自分の言葉で説明できること。 |
| 1.5 | **個別機能の実行（動作確認）** | | 完了 | Day 5 | - | **目的:** プロジェクトの主要な機能が自分のPCで正しく動くことを確認する。<br> **作業内容:**<br> - `README`の「使用方法」>「個別機能の実行」に記載のコマンドを、ダミーのID（例: `[GOOGLE_DOC_ID]`はテスト用のDocsのID）を使って実行してみる。<br> - エラーが出たら、メッセージを読み、環境変数の設定ミスなどがないか確認する。<br> **完了の定義:** 各コマンドがエラーなく実行できること（正常なエラーメッセージは除く）。 |
| 1.6 | **Supabaseのセットアップ** | | 未着手 | Day 6 | Supabaseプロジェクト | **目的:** WebApp用のデータベースとユーザー認証基盤を準備する。<br> **作業内容:**<br> - [Supabase](https://supabase.com)でアカウント作成<br> - 新規プロジェクトを作成（リージョン: 東京推奨）<br> - プロジェクトURLとAPIキーを取得<br> - SQL Editorで初期テーブルを作成（`migrations/`ディレクトリ参照）<br> - Row Level Security (RLS)ポリシーの設定<br> - Pythonクライアントライブラリでの接続テスト<br> **完了の定義:** PythonからSupabaseに接続し、データの読み書きができること。<br> **参考:** [Supabase Python クイックスタート](https://supabase.com/docs/reference/python/introduction) |
| 1.7 | **BigQueryのセットアップ** | | 未着手 | Day 7 | BigQueryデータセット | **目的:** 大規模データ分析用のデータウェアハウスを準備する。<br> **作業内容:**<br> - GCPコンソールでBigQueryデータセットを作成（`recruitment_data`, `client_learning`, `system_logs`）<br> - 初期テーブルスキーマを定義<br> - サンプルデータの投入テスト<br> - bqコマンドラインツールの動作確認<br> **完了の定義:** BigQueryにデータセットが作成され、サンプルクエリが実行できること。<br> **参考:** [BigQuery クイックスタート](https://cloud.google.com/bigquery/docs/quickstarts) |
| 1.8 | **RPOビジネスモデルの理解** | | 未着手 | Day 7 | - | **目的:** システムを正しく使うためにRPO業務の流れを理解する。<br> **作業内容:**<br> - RPO（採用代行）の基本的な業務フローを理解<br> - クライアント企業との関係性を把握<br> - スタッフの役割分担（admin/manager/operator）を理解<br> - `migrations/001_initial_schema.sql`を読んでデータモデルを理解<br> **完了の定義:** RPO業務フローとシステムの役割を説明できること。 |

---
### フェーズ2: WebApp開発 (目標: 2週間)

**目的:** ユーザーインターフェースとなるWebAppを開発し、採用要件管理を効率化する。

| No. | タスク名 | 担当 | 状態 | 期限 | 成果物 | 詳細 |
| :-- | :--- | :--- | :--- | :--- | :--- | :--- |
| 2.1 | **WebApp基盤構築** | | 未着手 | Day 8 | `src/web/main.py` | **目的:** FastAPIベースのWebアプリケーション基盤を構築する。<br> **作業内容:**<br> - FastAPIアプリケーションの初期設定<br> - Supabase Authとの連携設定<br> - Bootstrap/CSSの統合<br> - 基本的なルーティング設定<br> - CORS設定（必要に応じて）<br> **完了の定義:** `http://localhost:8000`でWebAppが起動し、ログイン画面が表示されること。 |
| 2.2 | **採用要件管理機能** | | 未着手 | Day 10 | `src/web/routers/requirements.py` | **目的:** Bizreach風フォームで採用要件を登録・管理する機能を実装。<br> **作業内容:**<br> - 採用要件入力フォームの作成（職種、年収、勤務地等）<br> - Cloud Functions APIとの連携<br> - 要件一覧表示機能<br> - 編集・削除機能<br> **完了の定義:** フォームから要件を登録し、一覧で確認できること。 |
| 2.3 | **実行管理機能** | | 未着手 | Day 12 | `src/web/routers/jobs.py` | **目的:** スクレイピング実行の指示と状況モニタリング機能を実装。<br> **作業内容:**<br> - 実行ボタンのUI作成<br> - Cloud Functions API呼び出し<br> - ジョブステータスのポーリング処理<br> - プログレスバーの表示<br> **完了の定義:** 実行ボタンを押すとジョブが開始し、進捗が確認できること。 |
| 2.4 | **結果確認機能** | | 未着手 | Day 14 | `src/web/routers/results.py` | **目的:** 処理結果の表示とGoogle Sheetsへのリンク機能を実装。<br> **作業内容:**<br> - 結果一覧表示画面の作成<br> - 統計情報の集計と表示<br> - Google Sheetsへのダイレクトリンク<br> - 完了通知の実装<br> **完了の定義:** 結果画面から処理結果を確認し、Sheetsにアクセスできること。 |
| 2.5 | **クライアント管理機能** | | 未着手 | Day 15 | `src/web/routers/clients.py` | **目的:** クライアント企業の情報を管理する機能を実装。<br> **作業内容:**<br> - クライアント企業の登録・編集・削除機能<br> - 担当者情報の管理<br> - クライアント別の設定管理（検索デフォルト値など）<br> - 候補者送客履歴の表示<br> **完了の定義:** クライアント企業の情報を登録・管理できること。 |

---
### フェーズ3: バックエンド処理の実装 (目標: 2週間)

**目的:** エージェントとCloud Functionsによるコア機能を実装する。

| No. | タスク名 | 担当 | 状態 | 期限 | 成果物 | 詳細 |
| :-- | :--- | :--- | :--- | :--- | :--- | :--- |
| 3.1 | **エージェント基盤構築** | | 未着手 | Day 18 | `src/agent/agent.py` | **目的:** 貸与PC上で動作するエージェントの基盤を構築。<br> **作業内容:**<br> - Pub/Subクライアントのセットアップ<br> - ポーリング処理の実装<br> - エラーハンドリング<br> - ログ出力設定<br> **完了の定義:** エージェントが起動し、Pub/Subからメッセージを受信できること。 |
| 3.2 | **Bizreachスクレイピング** | | 未着手 | Day 20 | `src/scraping/bizreach_scraper.py` | **目的:** Bizreachの候補者検索と情報取得を自動化。<br> **作業内容:**<br> - Playwrightでのログイン処理<br> - 検索条件の入力自動化<br> - 候補者情報の抽出<br> - データの構造化<br> **完了の定義:** 検索条件を渡すと候補者情報が取得できること。 |
| 3.3 | **Cloud Functions API** | | 未着手 | Day 22 | Cloud Functions | **目的:** WebAppとエージェントをつなぐAPIを実装。<br> **作業内容:**<br> - ジョブ作成APIの実装<br> - BigQuery操作処理<br> - Pub/Subメッセージ送信<br> - 結果受信処理<br> **完了の定義:** WebAppからのAPI呼び出しでジョブが作成されること。 |
| 3.4 | **AIマッチング判定** | | 未着手 | Day 24 | `src/ai/matching_engine.py` | **目的:** ChatGPT-4oを使ったマッチング判定の実装。<br> **作業内容:**<br> - OpenAI APIクライアント作成<br> - プロンプトエンジニアリング<br> - 判定結果の構造化<br> - スコアリングロジック<br> **完了の定義:** 要件と候補者情報からマッチングスコアが算出されること。 |
| 3.5 | **Google Sheets出力** | | 未着手 | Day 26 | `src/sheets/writer.py` | **目的:** AI判定結果をSheetsに出力する機能の実装。<br> **作業内容:**<br> - Google Sheets APIセットアップ<br> - データフォーマット定義<br> - 行追加処理の実装<br> - エラーハンドリング<br> **完了の定義:** 結果データがSheetsに正しく追記されること。 |

---
### フェーズ4: 統合テストとデプロイ (目標: 1週間)

**目的:** システムを安定稼働させ、より使いやすく、賢くする。

| No. | タスク名 | 担当 | 状態 | 期限 | 成果物 | 詳細 |
| :-- | :--- | :--- | :--- | :--- | :--- | :--- |
| 4.1 | **エラーハンドリングの強化** | | 未着手 | Day 20 | 各種ソースコード | **目的:** 特定の候補者で処理が失敗しても、システム全体が停止しないようにする。<br> **作業内容:**<br> - `try...except`構文を学ぶ。<br> - これまで実装した各機能（特に外部API連携やスクレイピング部分）に、エラーハンドリングを追加する。<br>   - 例: ログイン失敗、情報取得失敗、API通信エラーなど。<br> - エラーが発生した場合は、その情報をログに出力し、処理をスキップして次の候補者に移るようにする。<br> **完了の定義:** 意図的にエラー（例: 間違ったAPIキー）を発生させても、プログラムが異常終了せず、エラーログが記録されること。 |
| 4.2 | **テストコードの作成** | | 未着手 | Day 22 | `tests/` | **目的:** 機能の変更によって、既存の機能が壊れていないかを自動で確認できるようにする。<br> **作業内容:**<br> - `pytest`の基本的な使い方を学ぶ。<br> - `tests/unit/`ディレクトリに、各関数（例: `src/ai/matching_engine.py`の判定関数）の単体テストを書く。<br>   - ダミーの入力データを用意し、期待通りの出力が返ってくるか検証する。<br> **完了の定義:** `pytest tests/unit/` を実行すると、作成したテストがすべて成功（PASS）すること。 |
| 4.3 | **システム全体のデプロイ** | | 未着手 | Day 24 | - | **目的:** WebApp、Cloud Functions、エージェントを本番環境にデプロイする。<br> **作業内容:**<br> - WebAppをCloud Runにデプロイ<br> - Cloud Functions（API、結果処理）をデプロイ<br> - エージェントのインストーラー作成<br> - 環境変数の本番設定<br> **完了の定義:** 本番環境で全コンポーネントが正常に動作すること。 |
| 4.4 | **フィードバック機能の検討** | | 未着手 | Day 25 | `docs/feedback_design.md` | **目的:** AIの判定結果が正しかったか、人間がフィードバックする仕組みを考え、AIの精度向上に繋げる。<br> **作業内容:**<br> - スプレッドシートに「人間による最終判断」列を追加することを考える。<br> - そのフィードバックをどうやって収集し、どうやって次のAI判定のプロンプトに活かすか、アイデアをMarkdownファイルにまとめる。<br> **完了の定義:** フィードバックの仕組みに関する設計案がドキュメントとしてまとまっていること。 |

## テスト

```bash
# ユニットテスト
pytest tests/unit/

# 統合テスト
pytest tests/integration/

# カバレッジレポート
pytest --cov=src tests/
```

## デプロイ

### WebAppのデプロイ（Cloud Run）

```bash
# Dockerイメージのビルドとプッシュ
gcloud builds submit --tag gcr.io/[PROJECT]/rpo-webapp

# Cloud Runへのデプロイ
gcloud run deploy rpo-webapp \
    --image gcr.io/[PROJECT]/rpo-webapp \
    --platform managed \
    --region asia-northeast1 \
    --allow-unauthenticated
```

### Cloud Functions（制御系）のデプロイ

```bash
# API処理のデプロイ
gcloud functions deploy rpo-api \
    --runtime python39 \
    --trigger-http \
    --entry-point main \
    --set-env-vars PUBSUB_TOPIC=bizreach-jobs

# 結果処理のデプロイ
gcloud functions deploy rpo-result-processor \
    --runtime python39 \
    --trigger-topic bizreach-results \
    --entry-point process_results
```

### エージェントの設定（貸与PC）

```bash
# エージェントのインストール
python scripts/install_agent.py

# Windowsサービスとして登録（自動起動）
# または、スタートアップに登録して常駐化
```

## 運用

### 監視

- Cloud Logging でエラーログを監視
- BigQuery で処理統計を確認

### トラブルシューティング

よくある問題と対処法は[docs/troubleshooting.md](docs/troubleshooting.md)を参照

## ライセンス

[ライセンスタイプを記載]

## 貢献

プルリクエストを歓迎します。大きな変更の場合は、まずissueを作成して変更内容を議論してください。

## サポート

問題や質問がある場合は、GitHubのissueを作成してください。
