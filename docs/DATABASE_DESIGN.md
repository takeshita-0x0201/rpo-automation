# データベース設計

本システムはSupabase (PostgreSQL互換) をメインデータベースとして使用し、全てのデータを統合管理します。WebAppのマスターデータ、トランザクションデータ、候補者データ、AIマッチング結果など、システム全体のデータをSupabaseで管理します。

## Supabaseテーブル詳細設計

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
| job_type | TEXT | CHECK | ジョブタイプ（e.g., 'scraping', 'ai_matching'） |
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
| notification_type | TEXT | CHECK | 通知タイプ（e.g., 'email', 'in_app', 'slack'） |
| enabled | BOOLEAN | DEFAULT true | 有効/無効 |
| frequency | TEXT | | 通知頻度（e.g., 'instant', 'daily', 'weekly'） |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | 作成日時 |
| updated_at | TIMESTAMPTZ | DEFAULT NOW() | 更新日時 |

#### retry_queue（リトライキュー）
| カラム名 | 型 | 制約 | 説明 |
|---|---|---|---|
| id | UUID | PK | リトライID |
| operation_type | TEXT | NOT NULL | 操作タイプ（e.g., 'candidate_submission', 'ai_matching'） |
| payload | JSONB | NOT NULL | リトライに必要なデータ |
| retries_attempted | INTEGER | DEFAULT 0 | リトライ試行回数 |
| last_attempt_at | TIMESTAMPTZ | | 最終試行日時 |
| next_retry_at | TIMESTAMPTZ | NOT NULL | 次回リトライ日時 |
| status | TEXT | CHECK | ステータス（e.g., 'pending', 'retrying', 'failed', 'completed'） |
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

### 追加テーブル

#### candidates（候補者データ）
| カラム名 | 型 | 制約 | 説明 |
|---|---|---|---|
| id | UUID | PK | 候補者ID |
| search_id | TEXT | | 検索セッションID |
| session_id | TEXT | | スクレイピングセッションID |
| name | TEXT | | 氏名 |
| bizreach_id | TEXT | | BizreachID |
| bizreach_url | TEXT | | BizreachプロフィールURL |
| current_title | TEXT | | 現在の肩書き |
| current_position | TEXT | | 現在の役職 |
| current_company | TEXT | | 現在の会社 |
| experience_years | INTEGER | | 経験年数 |
| skills | TEXT[] | | スキル一覧 |
| education | TEXT | | 学歴 |
| profile_url | TEXT | | プロフィールURL |
| profile_summary | TEXT | | プロフィール概要 |
| scraped_at | TIMESTAMPTZ | NOT NULL | スクレイピング日時 |
| scraped_by | TEXT | | スクレイピング実行者 |
| platform | TEXT | DEFAULT 'bizreach' | プラットフォーム |
| scraped_data | JSONB | | 追加データ（client_id, requirement_id等） |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | 作成日時 |
| updated_at | TIMESTAMPTZ | DEFAULT NOW() | 更新日時 |

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

## インデックス設計

### Supabase
```sql
-- profiles
CREATE INDEX idx_profiles_role ON profiles(role);

-- clients  
CREATE INDEX idx_clients_active ON clients(is_active);

-- job_requirements
CREATE INDEX idx_requirements_client ON job_requirements(client_id);
CREATE INDEX idx_requirements_active ON job_requirements(is_active);

-- search_jobs
CREATE INDEX idx_jobs_user ON search_jobs(user_id);
CREATE INDEX idx_jobs_client ON search_jobs(client_id);
CREATE INDEX idx_jobs_status ON search_jobs(status);

-- candidates
CREATE INDEX idx_candidates_company ON candidates(current_company);
CREATE INDEX idx_candidates_bizreach_url ON candidates(bizreach_url);

-- search_results
CREATE INDEX idx_results_job ON search_results(search_job_id);
CREATE INDEX idx_results_score ON search_results(match_score DESC);
```

## データ保持ポリシー

### Supabase
- ユーザーデータ: 無期限保存
- ジョブデータ: 1年間保存後アーカイブ
- 候補者データ: 180日間保存後自動削除（テーブル設定で管理）
- AI評価結果: 1年間保存

## バックアップ戦略

### Supabase
- 日次自動バックアップ（Supabase Pro以上）
- 手動でのエクスポートスクリプト（週次）
- ポイントインタイムリカバリ: 7日間

## 監視とアラート

### パフォーマンス監視
- クエリ実行時間の監視
- テーブルサイズの増加率監視
- インデックス使用率の確認

### アラート設定
- ストレージ使用率 > 80%
- クエリ実行時間 > 2秒
- エラー率 > 5%

### スケーリング戦略
データ量が増加してパフォーマンス問題が発生した場合は、「[SupabaseからBigQueryへの移行ガイド](../bigquery_archive/supabase-to-bigquery-migration.md)」を参照してください。