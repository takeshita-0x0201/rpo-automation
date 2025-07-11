# データベース設計

## データベース概要

本システムは2つのデータベースサービスを使い分けることで、パフォーマンスとコストの最適化を実現します。

- **Supabase (PostgreSQL互換)**: WebAppのマスターデータ、トランザクションデータ、およびリアルタイムな参照・更新が必要なデータ
- **BigQuery**: 大規模データの蓄積と分析用のデータウェアハウス

## Supabase (PostgreSQL互換)

### 目的と役割

WebAppのメインDBとして、ユーザー管理、クライアント管理、採用要件のマスター、ジョブのステータス管理など、WebAppの機能に密接に関連するデータを扱います。

### テーブル設計

#### profiles（ユーザープロファイル）
| カラム名 | 型 | 制約 | 説明 |
|---|---|---|---|
| id | UUID | PK, FK(auth.users.id) | ユーザーID (Supabase Authと連携) |
| full_name | TEXT | | 氏名 |
| role | TEXT | CHECK | ロール（admin/user） |
| department | TEXT | | 所属部署 |
| avatar_url | TEXT | | アバター画像URL |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | 作成日時 |
| updated_at | TIMESTAMPTZ | DEFAULT NOW() | 更新日時 |

#### clients（クライアント企業）
| カラム名 | 型 | 制約 | 説明 |
|---|---|---|---|
| id | UUID | PK | クライアントID |
| name | TEXT | NOT NULL | 企業名 |
| industry | TEXT | | 業界 |
| size | TEXT | | 企業規模 |
| contact_person | TEXT | | 担当者名 |
| contact_email | TEXT | | 担当者メール |
| bizreach_search_url | TEXT | | Bizreach検索URL（オプション） |
| is_active | BOOLEAN | DEFAULT true | 有効フラグ |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | 作成日時 |
| updated_at | TIMESTAMPTZ | DEFAULT NOW() | 更新日時 |

#### client_settings（クライアント別設定）
| カラム名 | 型 | 制約 | 説明 |
|---|---|---|---|
| id | UUID | PK | 設定ID |
| client_id | UUID | FK(clients.id) | クライアントID |
| setting_key | TEXT | UNIQUE(client_id, setting_key) | 設定キー |
| setting_value | JSONB | | 設定値（JSON形式） |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | 作成日時 |
| updated_at | TIMESTAMPTZ | DEFAULT NOW() | 更新日時 |

#### job_requirements（採用要件マスター）
| カラム名 | 型 | 制約 | 説明 |
|---|---|---|---|
| id | UUID | PK | 要件ID |
| client_id | UUID | FK(clients.id) | クライアントID |
| title | TEXT | NOT NULL | タイトル |
| description | TEXT | | 詳細説明 |
| structured_data | JSON | | 構造化データ |
| is_active | BOOLEAN | DEFAULT true | 有効フラグ |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | 作成日時 |
| created_by | UUID | FK(profiles.id) | 作成者（profiles.id） |
| updated_at | TIMESTAMPTZ | DEFAULT NOW() | 更新日時 |

#### search_jobs（検索・AIマッチングジョブ）
| カラム名 | 型 | 制約 | 説明 |
|---|---|---|---|
| id | UUID | PK | ジョブID |
| user_id | UUID | FK(profiles.id) | 実行ユーザーID |
| client_id | UUID | FK(clients.id) | クライアントID |
| job_type | TEXT | CHECK | ジョブタイプ（'scraping', 'ai_matching'） |
| status | TEXT | CHECK | ステータス（pending/in_progress/completed/failed） |
| started_at | TIMESTAMPTZ | DEFAULT NOW() | 開始日時 |
| completed_at | TIMESTAMPTZ | | 完了日時 |
| total_candidates_processed | INTEGER | DEFAULT 0 | 処理候補者数 |
| job_parameters | JSONB | | ジョブ実行パラメータ（検索条件、要件IDなど） |
| error_details | TEXT | | エラー詳細 |

#### job_status_history（ジョブステータス履歴）
| カラム名 | 型 | 制約 | 説明 |
|---|---|---|---|
| id | UUID | PK | 履歴ID |
| job_id | UUID | FK(search_jobs.id) | ジョブID |
| status | TEXT | NOT NULL | ステータス |
| message | TEXT | | メッセージ |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | 作成日時 |

#### candidates（候補者マスター）
| カラム名 | 型 | 制約 | 説明 |
|---|---|---|---|
| id | UUID | PK | 候補者ID |
| bizreach_url | TEXT | UNIQUE | Bizreachの候補者URL |
| name | TEXT | | 氏名 |
| email | TEXT | UNIQUE | メールアドレス |
| phone | TEXT | | 電話番号 |
| current_company | TEXT | | 現在の会社 |
| current_position | TEXT | | 現在の役職 |
| experience_years | INTEGER | | 経験年数 |
| skills | TEXT[] | | スキル一覧 |
| education | TEXT | | 学歴 |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | 作成日時 |
| updated_at | TIMESTAMPTZ | DEFAULT NOW() | 更新日時 |

#### candidate_submissions（候補者データ提出履歴）
| カラム名 | 型 | 制約 | 説明 |
|---|---|---|---|
| id | UUID | PK | 提出履歴ID |
| candidate_id | UUID | FK(candidates.id) | 候補者ID |
| search_job_id | UUID | FK(search_jobs.id) | 関連する検索ジョブID |
| submission_time | TIMESTAMPTZ | DEFAULT NOW() | 提出日時 |
| source | TEXT | | データソース（e.g., 'Bizreach Extension'） |
| raw_data | JSONB | | 元のスクレイピング生データ |
| submitted_by_user_id | UUID | FK(profiles.id) | 提出者ユーザーID |

#### search_results（検索結果）
| カラム名 | 型 | 制約 | 説明 |
|---|---|---|---|
| id | UUID | PK | 結果ID |
| search_job_id | UUID | FK(search_jobs.id) | 関連する検索ジョブID |
| candidate_id | UUID | FK(candidates.id) | 候補者ID |
| job_requirement_id | UUID | FK(job_requirements.id) | 関連する採用要件ID |
| match_score | FLOAT | | マッチスコア（0-100） |
| match_reasons | TEXT[] | | マッチ理由のリスト |
| ai_evaluation_details | JSONB | | AI評価の詳細（JSON形式） |
| evaluated_at | TIMESTAMPTZ | DEFAULT NOW() | 評価日時 |

#### notification_settings（通知設定）
| カラム名 | 型 | 制約 | 説明 |
|---|---|---|---|
| id | UUID | PK | 設定ID |
| profile_id | UUID | FK(profiles.id) | ユーザープロファイルID |
| notification_type | TEXT | CHECK | 通知タイプ（'email', 'in_app', 'slack'） |
| enabled | BOOLEAN | DEFAULT true | 有効/無効 |
| frequency | TEXT | | 通知頻度（'instant', 'daily', 'weekly'） |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | 作成日時 |
| updated_at | TIMESTAMPTZ | DEFAULT NOW() | 更新日時 |

#### retry_queue（リトライキュー）
| カラム名 | 型 | 制約 | 説明 |
|---|---|---|---|
| id | UUID | PK | リトライID |
| operation_type | TEXT | NOT NULL | 操作タイプ（'candidate_submission', 'ai_matching'） |
| payload | JSONB | NOT NULL | リトライに必要なデータ |
| retries_attempted | INTEGER | DEFAULT 0 | リトライ試行回数 |
| last_attempt_at | TIMESTAMPTZ | | 最終試行日時 |
| next_retry_at | TIMESTAMPTZ | NOT NULL | 次回リトライ日時 |
| status | TEXT | CHECK | ステータス（'pending', 'retrying', 'failed', 'completed'） |
| error_message | TEXT | | エラーメッセージ |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | 作成日時 |
| updated_at | TIMESTAMPTZ | DEFAULT NOW() | 更新日時 |

### Row Level Security (RLS) ポリシー

- **profiles**: 本人のみ更新可能、adminは全て閲覧・更新可能
- **clients**: 全スタッフが閲覧可能、adminのみ編集可能
- **client_settings**: 関連するクライアントのスタッフが閲覧可能、adminのみ編集可能
- **job_requirements**: 関連するクライアントのスタッフが閲覧・編集可能、adminは全て閲覧・編集可能
- **search_jobs**: 本人のジョブのみ閲覧可能、adminは全て閲覧可能
- **job_status_history**: 関連するジョブのユーザーが閲覧可能、adminは全て閲覧可能
- **candidates**: 全スタッフが閲覧可能、adminのみ編集可能
- **candidate_submissions**: 関連するユーザーが閲覧可能、adminは全て閲覧可能
- **search_results**: 関連するジョブのユーザーが閲覧可能、adminは全て閲覧可能
- **notification_settings**: 本人のみ閲覧・更新可能
- **retry_queue**: adminのみ閲覧・更新可能

## AI評価結果テーブル

#### ai_evaluations（AI評価結果）
| カラム名 | 型 | 制約 | 説明 |
|---|---|---|---|
| id | UUID | PK | 評価ID |
| candidate_id | UUID | FK(candidates.id) | 候補者ID |
| requirement_id | UUID | FK(job_requirements.id) | 要件ID |
| search_id | TEXT | | 検索セッションID |
| ai_score | FLOAT | | AIスコア（0-1） |
| match_reasons | TEXT[] | | マッチ理由リスト |
| concerns | TEXT[] | | 懸念事項リスト |
| recommendation | TEXT | | 推薦レベル（high/medium/low） |
| detailed_evaluation | JSONB | | 詳細評価データ |
| evaluated_at | TIMESTAMPTZ | DEFAULT NOW() | 評価日時 |
| model_version | TEXT | | 使用したAIモデルバージョン |
| prompt_version | TEXT | | プロンプトバージョン |

#### searches（検索セッション）
| カラム名 | 型 | 制約 | 説明 |
|---|---|---|---|
| id | TEXT | PK | 検索ID |
| requirement_id | UUID | FK(job_requirements.id) | 要件ID |
| client_id | UUID | FK(clients.id) | クライアントID |
| started_at | TIMESTAMPTZ | NOT NULL | 開始日時 |
| completed_at | TIMESTAMPTZ | | 完了日時 |
| status | TEXT | | ステータス（running/completed/failed） |
| execution_mode | TEXT | | 実行モード（manual/scheduled） |
| total_candidates | INTEGER | | 総候補者数 |
| evaluated_candidates | INTEGER | | 評価済み候補者数 |
| matched_candidates | INTEGER | | マッチした候補者数 |
| error_message | TEXT | | エラーメッセージ |
| search_params | JSONB | | 検索パラメータ |
| created_by | UUID | FK(profiles.id) | 作成者 |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | 作成日時 |


## データフロー

### Phase 1: データ収集
1. Chrome拡張機能からのデータはSupabaseのcandidatesテーブルに保存
2. scraped_dataフィールドにclient_idやrequirement_idをJSON形式で格納
3. 候補者の重複はbizreach_idをキーとして排除

### Phase 2: AI判定  
1. Supabaseから候補者データを取得
2. AI判定結果をai_evaluationsテーブルに保存
3. 判定完了時にsearch_resultsに結果サマリーを保存

### データ整合性
- クライアント企業のデータは`client_id`で管理
- 候補者の重複はbizreach_idをキーとして排除  
- 全てのトランザクション処理はSupabaseで実行

## バックアップとリストア

### Supabase
- 自動バックアップ: 毎日
- ポイントインタイムリカバリ: 7日間
- 手動バックアップ: pg_dump利用可能
- データエクスポート: CSV/JSON形式でエクスポート可能

## 監視とアラート

### パフォーマンス監視
- 接続数、レスポンス時間
- クエリパフォーマンス
- インデックス使用率

### 容量監視
- データベースサイズ
- ストレージ使用量
- テーブル行数

### セキュリティ監視
- 異常なアクセスパターンの検知
- 失敗したログイン試行の監視
- データ変更の監査ログ

### スケーリング戦略
データ量が増加してパフォーマンス問題が発生した場合は、「[Supabaseから<NAME>への移行ガイド](../bigquery_archive/supabase-to-bigquery-migration.md)」を参照してください。