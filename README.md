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

### ユーザー権限と役割

本システムは、RPO事業者のスタッフの役割に応じて、2つの主要な権限グループ（ロール）を提供します。

#### 1. 管理者 (Admin)

**目的:** システム全体の管理、運用、監視を行う。

**主な機能と権限:**
- **ダッシュボード:** システム全体の統計情報（アクティブユーザー数、実行中ジョブ数など）や、システムの状態（APIサーバー、DB接続）を監視できる。
- **ユーザー管理:** システムを利用するスタッフのアカウント（`user`ロール）を作成、編集、削除できる。
- **クライアント割り当て:** 作成したユーザーに、担当するクライアント企業を割り当てることができる。
- **クライアント管理:** 取引先のクライアント企業情報を登録、編集、削除できる。
- **採用要件管理:** 全てのクライアントの採用要件を横断して管理できる。
- **ジョブ管理:** 全ての実行ジョブの状況を監視し、必要に応じてジョブの停止や再実行を行える。
- **分析レポート:** システムに蓄積されたデータから、高度な分析レポートを作成・閲覧できる。
- **システム設定:** アプリケーションの動作に関わる設定（AIモデルの選択、通知設定など）を変更できる。

#### 2. 一般ユーザー (User)

**目的:** 管理者から割り当てられた担当クライアントの採用業務を効率的に実行する。

**主な機能と権限:**
- **ダッシュボード:** 自分の担当業務に関連する情報（本日のタスク、最近の検索結果など）を一覧で確認できる。
- **採用要件管理:** 担当するクライアントの採用要件を作成、編集、削除できる。
- **候補者検索:** 登録した採用要件に基づき、Bizreachからの候補者検索を実行できる。
- **検索結果確認:** AIによるマッチング結果（スコア、理由）を確認し、レポートを出力できる。
- **実行履歴:** 自分が過去に実行したジョブの履歴を確認できる。

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

## FastAPIによるAPI統合アーキテクチャ

本システムでは、FastAPIが**API統合ハブ**として機能し、複数の外部サービスを統一されたインターフェースで提供しています。

### なぜFastAPIが必要か？

SupabaseやBigQuery、各種AI APIを直接クライアントから呼び出すのではなく、FastAPIを経由する理由：

1. **セキュリティ**: APIキーをクライアントに露出させない
2. **ビジネスロジック**: 複数サービスにまたがる複雑な処理を実装
3. **統一インターフェース**: 異なるサービスのAPIを統一された形式で提供
4. **認証・認可**: JWT認証による細かいアクセス制御
5. **エラーハンドリング**: 各サービスのエラーを統一形式に変換

### API統合の全体像

```mermaid
graph TB
    subgraph "フロントエンド"
        A[Webブラウザ<br/>React/Vue等]
        B[モバイルアプリ]
    end
    
    subgraph "FastAPI層（統一API）"
        C[FastAPI<br/>API Gateway]
        D[認証・認可<br/>JWT/OAuth2]
        E[ビジネスロジック]
        F[キャッシング<br/>Redis]
    end
    
    subgraph "外部サービス"
        G[Supabase<br/>ユーザー管理・DB]
        H[BigQuery<br/>大規模データ分析]
        I[OpenAI API<br/>ChatGPT-4o]
        J[Google APIs<br/>Docs/Sheets/Gemini]
        K[Bizreach<br/>スクレイピング]
    end
    
    A --> C
    B --> C
    
    C --> D
    D --> E
    E --> F
    
    E --> G
    E --> H
    E --> I
    E --> J
    E --> K
    
    style C fill:#f9f,stroke:#333,stroke-width:4px
    style E fill:#bbf,stroke:#333,stroke-width:2px
```

### 具体的な統合例

#### 1. 採用要件の登録フロー

```mermaid
sequenceDiagram
    participant UI as フロントエンド
    participant API as FastAPI
    participant Auth as Supabase Auth
    participant DB as Supabase DB
    participant BQ as BigQuery
    participant AI as Gemini API

    UI->>API: POST /api/requirements
    API->>Auth: トークン検証
    Auth-->>API: ユーザー情報
    API->>AI: 自然言語を構造化
    AI-->>API: JSON構造
    API->>DB: 基本情報を保存
    API->>BQ: 詳細データを保存
    API-->>UI: 統一レスポンス
```

#### 2. 候補者検索の実行フロー

```mermaid
sequenceDiagram
    participant UI as フロントエンド
    participant API as FastAPI
    participant Redis as Redis Cache
    participant Scraper as スクレイピング
    participant GPT as ChatGPT-4o
    participant BQ as BigQuery
    participant Sheets as Google Sheets

    UI->>API: POST /api/jobs/search
    API->>Redis: キャッシュ確認
    
    alt キャッシュなし
        API->>Scraper: 候補者取得
        Scraper-->>API: 候補者データ
        API->>GPT: マッチング判定
        GPT-->>API: スコア・理由
        API->>Redis: 結果をキャッシュ
    end
    
    API->>BQ: 結果を保存
    API->>Sheets: レポート生成
    API-->>UI: 統一レスポンス
```

### FastAPIの主要エンドポイント

| エンドポイント | メソッド | 統合サービス | 用途 |
|-------------|---------|------------|-----|
| `/api/auth/login` | POST | Supabase Auth | ユーザー認証 |
| `/api/requirements` | GET/POST | Supabase, BigQuery, Gemini | 採用要件の管理 |
| `/api/jobs` | POST | Pub/Sub, Cloud Functions | ジョブ実行管理 |
| `/api/candidates/{id}/evaluate` | POST | ChatGPT-4o, BigQuery | AI判定実行 |
| `/api/results/{job_id}` | GET | BigQuery, Google Sheets | 結果取得 |
| `/api/clients` | GET/POST | Supabase | クライアント管理 |

### 実装例：複数サービスを統合するAPI

```python
# src/web/routers/requirements.py の例
@router.post("/requirements")
async def create_requirement(
    requirement: RequirementCreate,
    current_user: User = Depends(get_current_user)
):
    # 1. Supabaseでユーザー権限確認
    if not check_user_permission(current_user.id, "create_requirement"):
        raise HTTPException(status_code=403)
    
    # 2. Gemini APIで自然言語を構造化
    structured_data = await gemini_client.structure_text(
        requirement.description
    )
    
    # 3. Supabaseに基本情報を保存
    db_record = await supabase.table("requirements").insert({
        "client_id": requirement.client_id,
        "title": requirement.title,
        "created_by": current_user.id
    }).execute()
    
    # 4. BigQueryに詳細データを保存
    await bigquery_client.insert_rows([{
        "id": db_record.data[0]["id"],
        "structured_data": structured_data,
        "original_text": requirement.description
    }])
    
    # 5. 統一されたレスポンスを返す
    return {
        "id": db_record.data[0]["id"],
        "status": "created",
        "structured_data": structured_data
    }
```

### メリットまとめ

- **開発効率**: フロントエンド開発者は1つのAPIだけ意識すればOK
- **保守性**: API仕様変更の影響を最小限に
- **拡張性**: 新しいサービス追加が容易
- **監視**: すべてのAPI呼び出しを一元的に監視・ログ記録
- **パフォーマンス**: キャッシングやバッチ処理で最適化

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

###### user_client_assignments（ユーザー・クライアント割り当て）
| カラム名 | 型 | 制約 | 説明 |
|---------|----|----|------|
| user_id | UUID | PK, FK(profiles) | 担当するRPOスタッフのID |
| client_id | UUID | PK, FK(clients) | 担当されるクライアントのID |
| assigned_at | TIMESTAMPTZ | DEFAULT NOW() | 割り当て日時 |

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

## WBS（作業計画書） - AI活用版

このセクションでは、本プロジェクトの開発タスクを詳細に分解したWBS（Work Breakdown Structure）を提示します。
**文系出身の新卒エンジニアがAIアシスタントと対話しながら、一人でタスクを理解し、実装まで進められる**ことを目標としています。

各タスクには、具体的な作業内容、AIへの質問例、完了の定義を記載しています。この通りに進めることで、プロジェクトの全体像を把握しながら、着実に開発を進めることができます。

---

### フェーズ1: 開発準備と全体像の理解 (目標: 1週間)

**目的:** プロジェクトを自分のPCで動かすための準備を整え、AIアシスタントに質問しながら、基本的な仕組みと技術要素を理解する。

| No. | タスク名 | 状態 | 詳細 |
| :-- | :--- | :--- | :--- |
| 1.1 | **開発環境のセットアップ** | 完了 | **目的:** Pythonコードを実行できる環境を整える。<br> **作業内容:**<br> 1. `README`の「前提条件」を確認し、Python 3.9以上をインストールする。<br> 2. `README`の「インストール」セクションに従い、リポジトリをクローンし、仮想環境(`venv`)を作成・有効化する。<br> 3. `pip install -r requirements.txt` を実行し、ライブラリをインストールする。<br> **AIへの質問例:**<br> - 「`git clone`って何をするコマンド？基本的な使い方を教えて」<br> - 「Pythonの`venv`って何？なぜ必要なの？」<br> - 「`pip install -r requirements.txt`は、何をしているの？」<br> **完了の定義:** `pip install`がエラーなく完了し、`pip list`でライブラリが一覧表示されること。 |
| 1.2 | **GCP/Google Workspaceのセットアップ** | 完了 | **目的:** プロジェクトが連携するGoogleのサービスを使えるようにする。<br> **作業内容:**<br> 1. `README`の「環境設定」に従い、`gcloud init`を実行し、GCPプロジェクトと連携させる。<br> 2. GCPコンソールで「BigQuery API」「Google Sheets API」を有効化する。<br> 3. サービスアカウントを作成し、キー（JSONファイル）をダウンロードする。<br> **AIへの質問例:**<br> - 「GCPのサービスアカウントって何？人とどう違うの？」<br> - 「GCPのIAMロールって何？『BigQueryデータ編集者』にはどんな権限があるの？」<br> **完了の定義:** `gcloud config list`で自分のプロジェクトが表示されること。サービスアカウントのJSONキーがダウンロードされていること。 |
| 1.3 | **環境変数の設定** | 完了 | **目的:** APIキーなどの秘密情報をコードから分離し、安全に管理する方法を学ぶ。<br> **作業内容:**<br> 1. `.env.example`をコピーして`.env`ファイルを作成する。<br> 2. `README`の「必要な環境変数」を参考に、ダウンロードしたGCPのキー情報や、別途用意したOpenAI/GeminiのAPIキーなどを`.env`ファイルに書き込む。<br> **AIへの質問例:**<br> - 「`.env`ファイルって何？なぜこれを使うとセキュリティが向上するの？」<br> - 「`python-dotenv`ライブラリの使い方を教えて。サンプルコードが欲しい」<br> **完了の定義:** `src/utils/env_loader.py`がエラーなく実行でき、環境変数が読み込めること。 |
| 1.4 | **プロジェクト構成の理解** | 完了 | **目的:** どこに何のコードがあるか把握し、変更するべきファイルを見つけられるようになる。<br> **作業内容:**<br> 1. `README`の「プロジェクト構成」を読み、各ディレクトリの役割を理解する。<br> 2. `src`内の各ディレクトリ（`agent`, `scraping`, `ai`, `web`等）を開き、ファイル名を眺めて、何をするためのコードか推測する。<br> **AIへの質問例:**<br> - 「一般的なPythonプロジェクトでは、`src`や`tests`ディレクトリにはそれぞれどんなファイルを置くのが普通？」<br> - 「`__init__.py`という空のファイルは何のためにあるの？」<br> **完了の定義:** 「Bizreachのスクレイピングロジックはどこ？」と聞かれて`src/scraping/bizreach.py`と答えられるなど、主要な機能とファイルの対応関係を説明できること。 |
| 1.5 | **Supabase/BigQueryのセットアップ** | 完了 | **目的:** WebAppのメインDBと、大規模データ用のDBを準備する。<br> **作業内容:**<br> 1. `README`の「Supabaseプロジェクトのセットアップ」セクションに従い、プロジェクト作成、テーブル作成、接続テストを行う。<br> 2. `README`の「BigQueryプロジェクトのセットアップ」セクションに従い、データセット作成、テーブル作成、接続テストを行う。<br> **AIへの質問例:**<br> - 「SupabaseとBigQueryはどう使い分けるの？それぞれの得意なことは？」<br> - 「SQLの`INSERT INTO`文の基本的な書き方を教えて」<br> - 「SupabaseのRLS（行レベルセキュリティ）って、どういう仕組み？」<br> **完了の定義:** `README`に記載のPython接続テストコードがエラーなく実行でき、データが取得できること。 |
| 1.6 | **RPOビジネスモデルの理解** | 未着手 | **目的:** このシステムが「誰の」「どんな課題を」解決するのかを理解する。<br> **作業内容:**<br> 1. RPO（採用代行）の基本的な業務フロー（クライアントから求人をもらう→候補者を探す→推薦する→結果を報告する）をネットで調べる。<br> 2. このシステムのユーザー（RPO事業者）が、どんな手作業に困っているか想像する。<br> 3. `README`のアーキテクチャ図を見て、どの部分が手作業を自動化しているか考える。<br> **AIへの質問例:**<br> - 「RPO事業のビジネスモデルについて、分かりやすく解説して」<br> - 「このシステムのアーキテクチャ図で、一番重要なコンポーネントはどれだと思う？その理由は？」<br> **完了の定義:** このシステムが解決する課題と、その解決方法の概要を自分の言葉で説明できること。 |

---

### フェーズ2: WebApp開発 (目標: 2週間)

**目的:** ユーザーが実際に操作する画面（フロントエンド）と、それに応答するAPI（バックエンド）の基礎を、FastAPIとSupabaseを使って構築する。

| No. | タスク名 | 状態 | 詳細 |
| :-- | :--- | :--- | :--- |
| 2.1 | **FastAPIで"Hello World"** | 完了 | **目的:** Webアプリケーションの最も基本的な仕組みを動かしてみる。<br> **作業内容:**<br> 1. `src/web/main.py`を作成する。<br> 2. FastAPIをインポートし、`app = FastAPI()`でインスタンスを作成する。<br> 3. `@app.get("/")`でルートエンドポイントを作成し、`{"message": "Hello World"}`を返す簡単な関数を定義する。<br> 4. `uvicorn src.web.main:app --reload`コマンドでサーバーを起動する。<br> **AIへの質問例:**<br> - 「FastAPIで最もシンプルなAPIを作る方法を教えて」<br> - 「`uvicorn`って何？`--reload`オプションにはどんな意味があるの？」<br> **完了の定義:** ブラウザで `http://localhost:8000` にアクセスし、`{"message": "Hello World"}` が表示されること。 |
| 2.2 | **クライアント企業の一覧表示** | 着手中 | **目的:** Supabaseデータベースからデータを取得し、Webページに表示する。<br> **作業内容:**<br> 1. **API実装:** `src/web/routers/clients.py`に、Supabaseから`clients`テーブルの全件を検索するAPIエンドポイント(`/api/clients`)を作成する。<br> 2. **HTMLテンプレート作成:** `src/web/templates/clients.html`を作成し、APIから受け取ったクライアント情報をテーブル形式で表示するHTMLを記述する。<br> 3. **ルーティング設定:** `src/web/main.py`で、`/clients`というパスへのアクセス時に`clients.html`を返すように設定する。<br> **AIへの質問例:**<br> - 「FastAPIでSupabaseに接続して、テーブルから全件取得するPythonコードを教えて」<br> - 「FastAPIでHTMLテンプレート(Jinja2)を返す基本的な方法を教えて」<br> - 「HTMLでテーブル（表）を作るにはどうすればいい？」<br> **完了の定義:** `http://localhost:8000/clients`にアクセスすると、Supabaseに登録したテスト用のクライアント企業一覧が表示されること。 |
| 2.3 | **クライアント企業の新規登録** | 未着手 | **目的:** Webフォームからの入力を受け取り、データベースに新しいデータを保存する。<br> **作業内容:**<br> 1. **入力フォーム作成:** `clients.html`に、企業名や担当者名を入力するHTMLフォーム(`<form>`)を追加する。<br> 2. **Pydanticモデル作成:** `src/web/models/client.py`に、フォームの入力に対応するPydanticモデルを作成し、データ型を定義する。<br> 3. **登録API実装:** `clients.py`に、フォームからのPOSTリクエストを受け取り、Pydanticモデルで検証し、Supabaseの`clients`テーブルにデータを`INSERT`するAPIエンドポイントを作成する。<br> **AIへの質問例:**<br> - 「HTMLの`<form>`タグの基本的な使い方を教えて。`action`と`method`って何？」<br> - 「FastAPIで、フォームからのデータを受け取るにはどうすればいい？Pydanticモデルの使い方も教えて」<br> - 「SupabaseのPythonクライアントで、新しい行をINSERTするコードを教えて」<br> **完了の定義:** Webページのフォームから新しいクライアント情報を入力・送信すると、ページがリロードされ、一覧に新しい企業が追加されていること。 |
| 2.4 | **採用要件管理機能の実装** | 未着手 | **目的:** プロジェクトのコア機能である採用要件のCRUD（作成・読み取り・更新・削除）を実装する。<br> **作業内容:**<br> 1. `2.2`, `2.3`を参考に、`採用要件`の「一覧表示機能」と「新規登録機能」を実装する。（`requirements.py`, `requirements.html`など）<br> 2. **編集機能:** 一覧の各行に「編集」ボタンを追加し、クリックすると既存データが入力されたフォームが表示されるページを作成。更新APIを実装する。<br> 3. **削除機能:** 一覧の各行に「削除」ボタンを追加し、クリックすると確認ダイアログを表示後、削除APIを呼び出すように実装する。<br> **AIへの質問例:**<br> - 「REST APIのCRUDってどういう意味？HTTPメソッド（GET, POST, PUT, DELETE）とどう対応するの？」<br> - 「JavaScriptで、ボタンクリック時に確認ダイアログ（`confirm`）を表示する方法は？」<br> **完了の定義:** WebApp上で採用要件の登録、一覧確認、編集、削除が一通り行えること。 |

---

### フェーズ3: バックエンド処理の実装 (目標: 2週間)

**目的:** システムの心臓部である、スクレイピング、AI判定、データ連携などの自動処理を実装する。

| No. | タスク名 | 状態 | 詳細 |
| :-- | :--- | :--- | :--- |
| 3.1 | **PlaywrightでBizreachにログイン** | 未着手 | **目的:** ブラウザ操作を自動化する第一歩として、ログイン処理を実装する。<br> **作業内容:**<br> 1. `src/scraping/bizreach.py`に、Playwrightを初期化し、ブラウザを起動するコードを書く。<br> 2. Bizreachのログインページにアクセスする。<br> 3. ユーザー名とパスワードの入力欄を特定し（CSSセレクタやXPathを使用）、`.fill()`メソッドで環境変数から読み込んだ認証情報を入力する。<br> 4. ログインボタンをクリックし、ログイン後のページに遷移したことを確認する（例: ページのタイトルやURLが変わるのを待つ）。<br> **AIへの質問例:**<br> - 「Playwrightの基本的な使い方を教えて。ブラウザを起動して特定のページに移動するコードは？」<br> - 「ブラウザのDevToolsで、入力欄のCSSセレクタを調べる方法を教えて」<br> - 「Playwrightで、ページが完全に読み込まれるのを待つにはどうすればいい？」<br> **完了の定義:** Pythonスクリプトを実行すると、ブラウザが自動で起動し、Bizreachにログインが成功すること。 |
| 3.2 | **候補者情報のスクレイピング** | 未着手 | **目的:** ログイン後のページから、候補者の情報を抽出し、構造化されたデータとして取得する。<br> **作業内容:**<br> 1. 候補者一覧ページで、一人の候補者情報が囲まれているHTML要素を特定する。<br> 2. `for`ループを使い、ページ内の全候補者要素を順番に処理する。<br> 3. 各候補者要素の中から、氏名、年齢、現在の会社名などのテキスト情報を、CSSセレクタを使って抽出する。<br> 4. 抽出した情報をPythonの辞書(`dict`)に格納し、リストに追加していく。<br> **AIへの質問例:**<br> - 「Playwrightで、特定の条件に一致する複数の要素を取得し、ループで処理する方法は？」<br> - 「Playwrightで、要素からテキストだけを取り出すにはどうすればいい？」<br> **完了の定義:** スクリプトを実行すると、候補者一覧ページに表示されている全員分の情報が、Pythonのリスト（辞書のリスト）として取得できること。 |
| 3.3 | **Cloud Functions APIの作成** | 一部完了 | **目的:** WebAppからの指示を受け取り、バックエンド処理を開始するトリガーとなるAPIを実装する。<br> **作業内容:**<br> 1. GCPコンソールで、HTTPトリガーのCloud Functionsを新規作成する。<br> 2. WebAppから送られてくる`requirement_id`をリクエストボディから受け取る。<br> 3. 受け取ったIDを基に、BigQueryから採用要件の詳細を取得する。<br> 4. 取得した要件を基に、Pub/Subにジョブメッセージを送信する。<br> **AIへの質問例:**<br> - 「Google Cloud FunctionsのHTTPトリガーの基本的な書き方を、Pythonで教えて」<br> - 「Cloud Functionsの中から、BigQueryのテーブルをクエリする方法は？」<br> - 「Cloud Functionsの中から、Pub/Subにメッセージを送信するコードを教えて」<br> **完了の定義:** WebAppの実行ボタンを押すと、Cloud Functionsが起動し、Pub/Subにジョブが送信されることがログで確認できること。 |
| 3.4 | **AIマッチング判定の実装** | 未着手 | **目的:** 採用要件と候補者情報を基に、AI（ChatGPT-4o）がマッチング度を判定する機能を実装する。<br> **作業内容:**<br> 1. `src/ai/matching_engine.py`に、OpenAIのAPIクライアントを初期化するコードを書く。<br> 2. **プロンプト作成:** 採用要件と候補者情報をテキストとして結合し、「この候補者は、この採用要件にどのくらいマッチしますか？スコアと理由をJSON形式で回答してください」という指示文（プロンプト）を作成する。<br> 3. 作成したプロンプトをOpenAI APIに送信し、結果を受け取る。<br> 4. AIからの返答（JSON文字列）をパースし、スコアや理由をBigQueryに保存する。<br> **AIへの質問例:**<br> - 「PythonでOpenAIのAPIを呼び出す基本的なコードを教えて」<br> - 「AIの性能を引き出すためのプロンプトのコツ（プロンプトエンジニアリング）を教えて」<br> - 「PythonでJSON文字列を辞書オブジェクトに変換するにはどうすればいい？」<br> **完了の定義:** 採用要件IDと候補者IDを渡すと、AIによる評価スコアと理由がBigQueryに保存されること。 |

---

### フェーズ4: 仕上げとデプロイ (目標: 1週間)

**目的:** システムを安定稼働させ、本番環境で使えるようにする。

| No. | タスク名 | 状態 | 詳細 |
| :-- | :--- | :--- | :--- |
| 4.1 | **エラーハンドリングの強化** | 未着手 | **目的:** 予期せぬエラーが発生しても、システム全体が停止しないように、堅牢性を高める。<br> **作業内容:**<br> 1. Pythonの`try...except`構文を学ぶ。<br> 2. 特に外部と通信する部分（スクレイピング、API呼び出し）に`try...except`を追加し、エラーが発生しても処理が継続するようにする。<br> 3. エラーが発生した場合は、その内容を`logging`ライブラリを使ってBigQueryのログテーブルに記録する。<br> **AIへの質問例:**<br> - 「Pythonの`try...except`の基本的な使い方を教えて。`Exception as e`って何？」<br> - 「Pythonの`logging`ライブラリの基本的な設定方法と、ファイルにログを出力する方法を教えて」<br> **完了の定義:** 意図的にエラー（例: 間違ったAPIキー）を発生させてもプログラムが異常終了せず、エラーログが記録されること。 |
| 4.2 | **単体テストの作成** | 未着手 | **目的:** 機能の変更によって、既存の機能が意図せず壊れていないかを確認する仕組みを作る。<br> **作業内容:**<br> 1. `pytest`の基本的な使い方を学ぶ。<br> 2. `tests/unit/`ディレクトリに、引数を渡すと決まった値を返すような単純な関数（例: `utils`内の関数）のテストコードを書く。<br> 3. ダミーの入力データを用意し、関数の返り値が期待通りの値になるかを`assert`で検証する。<br> **AIへの質問例:**<br> - 「`pytest`の基本的な使い方を教えて。テストファイルの命名規則や、簡単なテスト関数の書き方は？」<br> - 「`assert`文って何？テストでどう使うの？」<br> **完了の定義:** `pytest tests/unit/` を実行すると、作成したテストがすべて成功（PASS）すること。 |
| 4.3 | **WebAppのデプロイ** | 未着手 | **目的:** 開発したWebAppを、インターネット上の誰からでもアクセスできる本番環境（Cloud Run）で動かす。<br> **作業内容:**<br> 1. **Dockerfile作成:** WebAppをコンテナ化するための`Dockerfile`を作成する。<br> 2. **コンテナイメージのビルド:** `gcloud builds submit`コマンドを使い、ソースコードをCloud Buildに送信してコンテナイメージを作成する。<br> 3. **Cloud Runへのデプロイ:** `gcloud run deploy`コマンドを使い、ビルドしたイメージをCloud Runにデプロイする。<br> **AIへの質問例:**<br> - 「FastAPIアプリケーションをデプロイするための、基本的な`Dockerfile`を書いて」<br> - 「`gcloud builds submit`と`gcloud run deploy`コマンドの基本的な使い方を教えて」<br> **完了の定義:** デプロイ後に発行されるCloud RunのURLにアクセスすると、ローカル環境と同じようにWebAppが表示されること。 |


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
