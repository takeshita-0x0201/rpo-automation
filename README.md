# RPO自動化システム

AI・RPAツールを活用した採用代行業務（RPO）の自動化・効率化システム

## 概要

本システムは、RPO事業者がクライアント企業に代わってBizreachでの候補者スクリーニング、AIによる採用要件マッチング、結果のレポーティングまでを自動化するシステムです。貸与PCからのアクセスしか許可されないといったセキュリティ制約にも対応できる**エージェント型アーキテクチャ**と、クラウドからの**直接実行**を組み合わせた、柔軟な構成でRPO業務の効率化を実現します。

### システム利用者
- **メインユーザー**: RPO事業者のスタッフのみ
- **クライアント企業**: 採用要件を提供し、結果を受け取る（システムに直接アクセスしない）

## エンタープライズ向けアーキテクチャ

### システム構成の課題と解決策

本システムは、クライアントのセキュリティポリシーによりBizreachへのアクセスが貸与PCに限定される、といった制約がある環境でも柔軟に動作する必要があります。この課題を解決するため、貸与PCで動作する**エージェント型アーキテクチャ**を基本としつつ、制約のない環境ではクラウドから直接処理を実行できるハイブリッドな構成を採用しています。ユーザビリティ向上のため、**採用要件の管理や実行指示はWebApp**から行えるようにしています。

### 主要コンポーネントの役割

#### WebApp（ユーザーインターフェース）
- **採用要件管理**: Bizreach風フォームでの要件登録・編集
- **実行管理**: スクレイピング実行指示と状況モニタリング
- **結果確認**: 処理完了通知とGoogle Sheetsへのリンク

#### バックエンド処理（自動化の心臓部）
- **スクレイピング**: クライアントの制約に応じて、貸与PCエージェントまたはCloud Functionsで実行
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

### ハイブリッドアーキテクチャの主な特徴

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

### バックエンドの主な役割
- **Pub/Subポーリング**: 貸与PCエージェントが実行
- **BigQuery操作**: Cloud Functions経由で実行
- **スクレイピング**: 貸与PCエージェントまたはCloud Functionsが実行

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
2. クライアント設定に基づいて実行方式を判定
   - `allows_direct_scraping = true` → Cloud Functions直接実行
   - `allows_direct_scraping = false` → エージェント経由実行
3. 選択された方式で候補者検索を実行
4. 結果をBigQueryに保存

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
    CF->>BQ: 6. 要件データとクライアント設定を取得

    alt allows_direct_scraping = false (エージェント経由)
        CF->>PS: 7a. ジョブメッセージ投稿
        Agent->>PS: 8a. ポーリング & ジョブ受信
        Agent->>Agent: 9a. スクレイピング実行
        Agent->>PS: 10a. 候補者データを結果Topicへ送信
    else allows_direct_scraping = true (直接実行)
        CF->>CF: 7b. 直接スクレイピング実行
        CF->>PS: 8b. 候補者データを結果Topicへ送信
    end

    PS->>CF: 11. 結果を受信
    CF->>CF: 12. AI判定実行
    CF->>BQ: 13. 結果保存
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
- **ハイブリッド実行モデル**: セキュリティ制約に応じて実行方式を自動で切り替え
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
2. **候補者検索**: クライアント設定に応じて実行方式を選択
   - セキュリティ制約なし → Cloud Functions直接実行（〜90人、9分以内）
   - セキュリティ制約あり → 貸与PCエージェント経由（人数・時間無制限）
3. **AI判定**: 要件と候補者のマッチング判定（ChatGPT-4o）
4. **結果出力**: Google Sheetsへ結果を記録
5. **フィードバック**: クライアント別の採用パターンを学習データとして蓄積

### データベース設計

本システムは2つのデータベースサービスを使い分けることで、パフォーマンスとコストの最適化を実現します。

#### 1. Supabase (PostgreSQL互換)
**目的**: WebAppのリアルタイム処理とトランザクション管理

##### Supabaseテーブル詳細設計

###### profiles（RPOスタッフプロファイル）
| カラム名 | 型 | 制約 | 説明 |
|---------|----|----|------|
| id | UUID | PK, FK(auth.users) | Supabase AuthのユーザーID |
| full_name | TEXT | | スタッフの氏名 |
| role | TEXT | CHECK | 役職（admin/manager/operator） |
| department | TEXT | | 所属部署 |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | 作成日時 |
| updated_at | TIMESTAMPTZ | DEFAULT NOW() | 更新日時 |

###### clients（クライアント企業）
| カラム名 | 型 | 制約 | 説明 |
|---------|----|----|------|
| id | UUID | PK | クライアントID |
| name | TEXT | NOT NULL | 企業名 |
| industry | TEXT | | 業界 |
| size | TEXT | | 企業規模 |
| contact_person | TEXT | | 担当者名 |
| contact_email | TEXT | | 担当者メール |
| allows_direct_scraping | BOOLEAN | DEFAULT false | 直接スクレイピング許可フラグ |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | 作成日時 |
| updated_at | TIMESTAMPTZ | DEFAULT NOW() | 更新日時 |

###### jobs（実行ジョブ）
| カラム名 | 型 | 制約 | 説明 |
|---------|----|----|------|
| id | UUID | PK | ジョブID |
| requirement_id | TEXT | NOT NULL | 採用要件ID（BigQuery参照） |
| client_id | UUID | FK(clients) | クライアントID |
| status | TEXT | CHECK | ステータス（pending/running/completed/failed） |
| created_by | UUID | FK(auth.users) | 作成者 |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | 作成日時 |
| updated_at | TIMESTAMPTZ | DEFAULT NOW() | 更新日時 |
| completed_at | TIMESTAMPTZ | | 完了日時 |
| error_message | TEXT | | エラーメッセージ |
| candidate_count | INTEGER | DEFAULT 0 | 取得候補者数 |

###### job_status_history（ジョブステータス履歴）
| カラム名 | 型 | 制約 | 説明 |
|---------|----|----|------|
| id | UUID | PK | 履歴ID |
| job_id | UUID | FK(jobs) | ジョブID |
| status | TEXT | NOT NULL | ステータス |
| message | TEXT | | メッセージ |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | 作成日時 |

###### client_settings（クライアント設定）
| カラム名 | 型 | 制約 | 説明 |
|---------|----|----|------|
| client_id | UUID | PK, FK(clients) | クライアントID |
| search_defaults | JSONB | DEFAULT '{}' | 検索デフォルト値 |
| scoring_weights | JSONB | DEFAULT '{}' | スコアリング重み |
| custom_terms | JSONB | DEFAULT '{}' | カスタム用語辞書 |
| max_candidates_per_batch | INTEGER | DEFAULT 80 | バッチあたり最大候補者数 |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | 作成日時 |
| updated_at | TIMESTAMPTZ | DEFAULT NOW() | 更新日時 |

###### Row Level Security (RLS) ポリシー
- **profiles**: 全員が閲覧可能、本人のみ更新可能
- **clients**: 全スタッフが閲覧可能、admin/managerのみ編集可能
- **jobs**: 全スタッフが閲覧・編集可能
- **client_settings**: admin/managerのみ編集可能

#### 2. BigQuery
**目的**: 大規模データの蓄積と分析

##### BigQueryテーブル詳細設計

###### recruitment_data.requirements（採用要件）
| カラム名 | 型 | 説明 |
|---------|----|----|
| id | STRING | 要件ID |
| client_id | STRING | クライアントID |
| title | STRING | 募集タイトル |
| position | STRING | 職種 |
| description | STRING | 詳細説明 |
| required_skills | ARRAY<STRING> | 必須スキル |
| preferred_skills | ARRAY<STRING> | 歓迎スキル |
| experience_years | INTEGER | 必要経験年数 |
| education_level | STRING | 学歴要件 |
| salary_range | STRUCT | 給与レンジ |
| work_location | STRING | 勤務地 |
| employment_type | STRING | 雇用形態 |
| original_text | STRING | 原本テキスト |
| structured_data | JSON | 構造化データ |
| created_at | TIMESTAMP | 作成日時 |
| created_by | STRING | 作成者ID |

###### recruitment_data.candidates（候補者）
| カラム名 | 型 | 説明 |
|---------|----|----|
| id | STRING | 候補者ID |
| search_id | STRING | 検索ID |
| name | STRING | 候補者名 |
| current_title | STRING | 現在の役職 |
| current_company | STRING | 現在の企業 |
| experience_years | INTEGER | 経験年数 |
| skills | ARRAY<STRING> | スキルセット |
| education | STRING | 学歴 |
| profile_url | STRING | プロフィールURL |
| scraped_data | JSON | スクレイピングデータ |
| scraped_at | TIMESTAMP | 取得日時 |

###### recruitment_data.ai_evaluations（AI評価）
| カラム名 | 型 | 説明 |
|---------|----|----|
| id | STRING | 評価ID |
| candidate_id | STRING | 候補者ID |
| requirement_id | STRING | 要件ID |
| ai_score | FLOAT64 | AIスコア（0-100） |
| match_reasons | ARRAY<STRING> | マッチング理由 |
| concerns | ARRAY<STRING> | 懸念点 |
| recommendation | STRING | 推奨度 |
| evaluated_at | TIMESTAMP | 評価日時 |
| model_version | STRING | AIモデルバージョン |

##### データパーティショニング戦略
- **requirements**: created_at で日付パーティション
- **candidates**: scraped_at で日付パーティション
- **ai_evaluations**: evaluated_at で日付パーティション
- 90日以上古いデータは自動的にコールドストレージへ

#### データベース連携
- Supabaseの実行完了ジョブは、バッチでBigQueryへ転送
- BigQueryの集計結果は、必要に応じてSupabaseにキャッシュ
- クライアント企業のデータは`client_id`で管理

### セキュリティ設計

#### 環境別の認証情報管理
| 環境 | 管理方法 | 用途 |
|------|---------|-----|
| 開発環境 | .env.development | テストアカウントのみ使用 |
| エージェントPC | ローカル.env | 貸与PC内で安全に管理 |
| 本番Cloud | Secret Manager | 暗号化して保管、IAMで権限制御 |

#### アクセス制御
- **最小権限の原則**: 各サービスアカウントは必要最小限の権限のみ付与
- **役職別アクセス**: 
  - operator: 自分の担当クライアントのみ
  - manager: 全クライアントの閲覧・実行
  - admin: システム設定変更権限

#### 監査とコンプライアンス
- 全API呼び出しをBigQuery audit_logsに記録
- 個人情報へのアクセスは詳細ログを保持
- ログは90日間保持後、自動アーカイブ
- 定期的なセキュリティレビューの実施

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

### Supabaseプロジェクトのセットアップ

#### 1. Supabaseアカウントの作成
1. [Supabase](https://supabase.com)にアクセス
2. GitHubアカウントまたはメールでサインアップ
3. 新規プロジェクトを作成
   - プロジェクト名: `rpo-automation`
   - データベースパスワード: 安全なパスワードを設定（後で使用）
   - リージョン: `Northeast Asia (Tokyo)` を推奨
   - 料金プラン: Free tier（開発・テスト用）

#### 2. プロジェクト情報の取得
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

#### 3. データベーススキーマの作成
1. Supabaseダッシュボードの「SQL Editor」を開く
2. 「New query」をクリック
3. 以下のSQLを実行してテーブルを作成：

```sql
-- migrations/001_initial_schema.sql の内容をコピー＆ペースト
```

または、プロジェクトのSQLファイルを直接実行：
```bash
# Supabase CLIを使用する場合（要インストール）
supabase db push --db-url "postgresql://postgres:[PASSWORD]@db.[PROJECT_ID].supabase.co:5432/postgres"
```

#### 4. 認証設定
1. Authentication → Settings で以下を確認：
   - Email認証が有効になっていること
   - サイトURL: `http://localhost:8000`（開発環境）
   - リダイレクトURL: `http://localhost:8000/auth/callback`

2. Authentication → Users でテストユーザーを作成：
   - Email: `admin@example.com`
   - Password: 任意のパスワード

#### 5. 初期データの投入
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
INSERT INTO clients (name, industry, size, contact_person, contact_email, allows_direct_scraping)
VALUES 
    ('株式会社テストA', 'IT', '100-500名', '採用担当A', 'recruit-a@example.com', true),
    ('株式会社テストB', '製造業', '500-1000名', '採用担当B', 'recruit-b@example.com', false);
```

#### 6. 接続テスト
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

### BigQueryプロジェクトのセットアップ

#### 1. BigQuery APIの有効化
1. [GCPコンソール](https://console.cloud.google.com)にアクセス
2. 「APIとサービス」→「ライブラリ」
3. 「BigQuery API」を検索して有効化
4. 「Cloud Resource Manager API」も同様に有効化

#### 2. データセットの作成
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

#### 3. テーブルの作成
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

#### 4. サービスアカウントの作成
1. IAMと管理 → サービスアカウント → 「作成」
2. サービスアカウント名: `rpo-automation-bigquery`
3. 役割を付与:
   - BigQuery データ編集者
   - BigQuery ジョブユーザー
4. キーを作成（JSON形式）してダウンロード

#### 5. 環境変数の設定
ダウンロードしたキーファイルのパスを環境変数に設定：

```bash
# .envファイル
GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/service-account-key.json
BIGQUERY_PROJECT_ID=your-project-id
BIGQUERY_DATASET=recruitment_data
```

#### 6. 接続テスト
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

#### 7. スケジュールドクエリの設定（オプション）
日次レポート生成などの定期処理を設定：

1. BigQueryコンソール → 「スケジュールドクエリ」
2. 「スケジュールドクエリを作成」
3. クエリ例：
```sql
CALL system_logs.archive_old_logs();
```
4. スケジュール: 毎日午前2時（JST）

#### 8. コスト管理のベストプラクティス
- **パーティショニング**: 日付カラムでパーティション分割済み
- **クラスタリング**: 頻繁に使用するカラムでクラスタリング済み
- **有効期限**: 90日以上古いデータは自動アーカイブ
- **クエリの最適化**: 必要なカラムのみSELECT
- **プレビュー**: クエリ実行前にコスト見積もりを確認

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
- `OPENAI_API_KEY`: OpenAI APIキー（Secret Manager推奨）
- `GEMINI_API_KEY`: Gemini APIキー（Secret Manager推奨）
- `GOOGLE_SHEETS_ID`: 出力先のGoogle Sheets ID
- `PUBSUB_TOPIC`: Pub/Subトピック名
- `PUBSUB_SUBSCRIPTION`: Pub/Subサブスクリプション名
- `SECRET_MANAGER_PROJECT`: Secret Manager用プロジェクトID

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

# スクレイピング実行（直接実行）
python -m src.scraping.direct_executor --client-id [CLIENT_ID] --criteria "Python 5年"

# スクレイピング実行（エージェント経由）
python -m src.agent.executor --client-id [CLIENT_ID] --job-id [JOB_ID]
```

## WBS（作業計画書）

このセクションでは、本プロジェクトの開発タスクを詳細に分解したWBS（Work Breakdown Structure）を提示します。
文系出身の新卒エンジニアが一人でタスクを理解し、実装まで進められるように、各タスクの目的、具体的な作業内容、完了の定義、参考情報を記載しています。

### 進捗サマリー（2025年1月7日時点）
- **フェーズ1: 環境構築と基礎理解** - 7/9タスク完了（78%）
  - ✅ 開発環境、GCP、環境変数、プロジェクト構成理解、動作確認、Supabase、BigQuery
  - ⏳ RPOビジネスモデル理解、Secret Manager設定
- **フェーズ2: WebApp開発** - 4/5タスク着手（80%）
  - ✅ WebApp基盤構築（完了）
  - 🔄 採用要件管理、実行管理、結果確認機能（着手中）
  - ⏳ クライアント管理
- **フェーズ3: バックエンド処理** - 1/5タスク着手（20%）
  - 🔄 Cloud Functions API（一部完了）
  - ⏳ エージェント基盤、スクレイピング、AI判定、Sheets出力
- **フェーズ4: 統合テストとデプロイ** - 未着手

### フェーズ1: 環境構築と基礎理解 (目標: 1週間)

**目的:** プロジェクトを自分のPCで動かすための準備を整え、基本的な仕組みを理解する。

| No. | タスク名 | 担当 | 状態 | 期限 | 成果物 | 詳細 |
| :-- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1.1 | **開発環境のセットアップ** | | 完了 | Day 1 | - | **目的:** Pythonコードを実行できる環境を整える。<br> **作業内容:**<br> - `README`の「前提条件」を確認し、Python 3.9以上がインストールされているか確認する (`python --version`)。<br> - `README`の「インストール」セクションに従い、リポジトリをクローンし、仮想環境(`venv`)を作成・有効化する。<br> - `pip install -r requirements.txt` を実行し、必要なライブラリをインストールする。<br> **完了の定義:** エラーなく`pip install`が完了し、`pip list`でライブラリが確認できること。 |
| 1.2 | **GCP/Google Workspaceのセットアップ** | | 完了 | Day 2 | - | **目的:** プロジェクトが連携するGoogleサービスを使えるようにする。<br> **作業内容:**<br> - `README`の「環境設定」に従い、`gcloud init`を実行し、手持ちのGCPプロジェクトと連携させる。<br> - Google Docs, Google Sheets APIを有効化する。<br> - サービスアカウントを作成し、キー（JSONファイル）をダウンロードする。<br> **完了の定義:** `gcloud config list`で自分のプロジェクトが表示されること。APIが有効化されていること。 |
| 1.3 | **環境変数の設定** | | 完了 | Day 3 | `.env`ファイル | **目的:** APIキーなどの秘密情報をコードから分離し、安全に管理する。<br> **作業内容:**<br> - `cp .env.example .env` を実行し、`.env`ファイルを作成する。<br> - `README`の「必要な環境変数」セクションを参考に、ダウンロードしたGCPのキー情報や、別途用意したOpenAI/GeminiのAPIキーなどを`.env`ファイルに書き込む。<br> **完了の定義:** 全ての必須環境変数が`.env`ファイルに設定されていること。 |
| 1.4 | **プロジェクト構成の理解** | | 完了 | Day 4 | - | **目的:** どこに何のコードがあるか把握する。<br> **作業内容:**<br> - `README`の「プロジェクト構成」を見る。<br> - `src`ディレクトリ内の各サブディレクトリ（`scraping`, `ai`, `data`, `sheets`, `utils`）の役割を推測する。<br> - 各ディレクトリ内のPythonファイル名を眺め、何をするためのファイルか想像してみる。<br> **完了の定義:** 各ディレクトリの役割を自分の言葉で説明できること。 |
| 1.5 | **個別機能の実行（動作確認）** | | 完了 | Day 5 | - | **目的:** プロジェクトの主要な機能が自分のPCで正しく動くことを確認する。<br> **作業内容:**<br> - `README`の「使用方法」>「個別機能の実行」に記載のコマンドを、ダミーのID（例: `[GOOGLE_DOC_ID]`はテスト用のDocsのID）を使って実行してみる。<br> - エラーが出たら、メッセージを読み、環境変数の設定ミスなどがないか確認する。<br> **完了の定義:** 各コマンドがエラーなく実行できること（正常なエラーメッセージは除く）。 |
| 1.6 | **Supabaseのセットアップ** | | 完了 | Day 6 | Supabaseプロジェクト | **目的:** WebApp用のデータベースとユーザー認証基盤を準備する。<br> **作業内容:**<br> - [Supabase](https://supabase.com)でアカウント作成<br> - 新規プロジェクトを作成（リージョン: 東京推奨）<br> - プロジェクトURLとAPIキーを取得<br> - SQL Editorで初期テーブルを作成（`migrations/`ディレクトリ参照）<br> - Row Level Security (RLS)ポリシーの設定<br> - Pythonクライアントライブラリでの接続テスト<br> **完了の定義:** PythonからSupabaseに接続し、データの読み書きができること。<br> **参考:** [Supabase Python クイックスタート](https://supabase.com/docs/reference/python/introduction) |
| 1.7 | **BigQueryのセットアップ** | | 完了 | Day 7 | BigQueryデータセット | **目的:** 大規模データ分析用のデータウェアハウスを準備する。<br> **作業内容:**<br> - GCPコンソールでBigQueryデータセットを作成（`recruitment_data`, `client_learning`, `system_logs`）<br> - 初期テーブルスキーマを定義<br> - サンプルデータの投入テスト<br> - bqコマンドラインツールの動作確認<br> **完了の定義:** BigQueryにデータセットが作成され、サンプルクエリが実行できること。<br> **参考:** [BigQuery クイックスタート](https://cloud.google.com/bigquery/docs/quickstarts) |
| 1.8 | **RPOビジネスモデルの理解** | | 未着手 | Day 7 | - | **目的:** システムを正しく使うためにRPO業務の流れを理解する。<br> **作業内容:**<br> - RPO（採用代行）の基本的な業務フローを理解<br> - クライアント企業との関係性を把握<br> - スタッフの役割分担（admin/manager/operator）を理解<br> - `migrations/001_initial_schema.sql`を読んでデータモデルを理解<br> **完了の定義:** RPO業務フローとシステムの役割を説明できること。 |
| 1.9 | **Secret Managerの設定** | | 未着手 | Day 7 | Secret設定完了 | **目的:** 本番環境の認証情報を安全に管理する。<br> **作業内容:**<br> - GCPコンソールでSecret Managerを有効化<br> - Bizreach認証情報をSecretとして登録<br> - APIキー類をSecretとして登録<br> - サービスアカウントにアクセス権限付与<br> - Pythonコードからの読み取りテスト<br> **完了の定義:** コードからSecretを取得できること。<br> **参考:** [Secret Manager クイックスタート](https://cloud.google.com/secret-manager/docs/quickstart) |

---
### フェーズ2: WebApp開発 (目標: 2週間)

**目的:** ユーザーインターフェースとなるWebAppを開発し、採用要件管理を効率化する。

| No. | タスク名 | 担当 | 状態 | 期限 | 成果物 | 詳細 |
| :-- | :--- | :--- | :--- | :--- | :--- | :--- |
| 2.1 | **WebApp基盤構築** | | 完了 | Day 8 | `src/web/main.py` | **目的:** FastAPIベースのWebアプリケーション基盤を構築する。<br> **作業内容:**<br> - FastAPIアプリケーションの初期設定<br> - Supabase Authとの連携設定<br> - Bootstrap/CSSの統合<br> - 基本的なルーティング設定<br> - CORS設定（必要に応じて）<br> **完了の定義:** `http://localhost:8000`でWebAppが起動し、ログイン画面が表示されること。 |
| 2.2 | **採用要件管理機能** | | 着手中 | Day 10 | `src/web/routers/requirements.py` | **目的:** Bizreach風フォームで採用要件を登録・管理する機能を実装。<br> **作業内容:**<br> - 採用要件入力フォームの作成（職種、年収、勤務地等）<br> - Cloud Functions APIとの連携<br> - 要件一覧表示機能<br> - 編集・削除機能<br> **完了の定義:** フォームから要件を登録し、一覧で確認できること。 |
| 2.3 | **実行管理機能** | | 着手中 | Day 12 | `src/web/routers/jobs.py` | **目的:** スクレイピング実行の指示と状況モニタリング機能を実装。<br> **作業内容:**<br> - 実行ボタンのUI作成<br> - Cloud Functions API呼び出し<br> - ジョブステータスのポーリング処理<br> - プログレスバーの表示<br> **完了の定義:** 実行ボタンを押すとジョブが開始し、進捗が確認できること。 |
| 2.4 | **結果確認機能** | | 着手中 | Day 14 | `src/web/routers/results.py` | **目的:** 処理結果の表示とGoogle Sheetsへのリンク機能を実装。<br> **作業内容:**<br> - 結果一覧表示画面の作成<br> - 統計情報の集計と表示<br> - Google Sheetsへのダイレクトリンク<br> - 完了通知の実装<br> **完了の定義:** 結果画面から処理結果を確認し、Sheetsにアクセスできること。 |
| 2.5 | **クライアント管理機能** | | 未着手 | Day 15 | `src/web/routers/clients.py` | **目的:** クライアント企業の情報を管理する機能を実装。<br> **作業内容:**<br> - クライアント企業の登録・編集・削除機能<br> - 担当者情報の管理<br> - クライアント別の設定管理（検索デフォルト値など）<br> - 候補者送客履歴の表示<br> **完了の定義:** クライアント企業の情報を登録・管理できること。 |

---
### フェーズ3: バックエンド処理の実装 (目標: 2週間)

**目的:** エージェントとCloud Functionsによるコア機能を実装する。

| No. | タスク名 | 担当 | 状態 | 期限 | 成果物 | 詳細 |
| :-- | :--- | :--- | :--- | :--- | :--- | :--- |
| 3.1 | **エージェント基盤構築** | | 未着手 | Day 18 | `src/agent/agent.py` | **目的:** 貸与PC上で動作するエージェントの基盤を構築。<br> **作業内容:**<br> - Pub/Subクライアントのセットアップ<br> - ポーリング処理の実装<br> - エラーハンドリング<br> - ログ出力設定<br> **完了の定義:** エージェントが起動し、Pub/Subからメッセージを受信できること。 |
| 3.2 | **Bizreachスクレイピング** | | 未着手 | Day 20 | `src/scraping/bizreach_scraper.py` | **目的:** Bizreachの候補者検索と情報取得を自動化。<br> **作業内容:**<br> - Playwrightでのログイン処理<br> - 検索条件の入力自動化<br> - 候補者情報の抽出<br> - データの構造化<br> **完了の定義:** 検索条件を渡すと候補者情報が取得できること。 |
| 3.3 | **Cloud Functions API** | | 一部完了 | Day 22 | Cloud Functions | **目的:** WebAppとエージェントをつなぐAPIを実装。<br> **作業内容:**<br> - ジョブ作成APIの実装<br> - BigQuery操作処理<br> - Pub/Subメッセージ送信<br> - 結果受信処理<br> **完了の定義:** WebAppからのAPI呼び出しでジョブが作成されること。 |
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
