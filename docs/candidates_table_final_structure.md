# Candidatesテーブル最終構造

## 必須カラム構成

### 1. 基本カラム（既存維持）
| カラム名 | 型 | 説明 |
|---------|-----|------|
| id | UUID | 主キー（自動生成） |
| created_at | TIMESTAMPTZ | 作成日時（自動設定） |
| updated_at | TIMESTAMPTZ | 更新日時（自動更新） |

### 2. スクレイピングデータカラム（新規/変更）
| カラム名 | 型 | 必須 | 説明 |
|---------|-----|------|------|
| candidate_id | TEXT | ✓ | プラットフォーム上の候補者ID |
| candidate_link | TEXT | ✓ | 候補者プロフィールURL |
| candidate_company | TEXT | | 所属企業名 |
| candidate_resume | TEXT | | レジュメ情報（URLまたはテキスト） |
| platform | TEXT | ✓ | プラットフォーム名（デフォルト: 'bizreach'） |

### 3. メタデータカラム
| カラム名 | 型 | 説明 |
|---------|-----|------|
| scraped_at | TIMESTAMPTZ | スクレイピング実行日時 |
| scraped_by | UUID | スクレイピング実行者（profiles.id） |

### 4. リレーションカラム
| カラム名 | 型 | 説明 |
|---------|-----|------|
| client_id | UUID | クライアントID（外部キー） |
| requirement_id | UUID | 採用要件ID（外部キー） |
| scraping_session_id | UUID | スクレイピングセッションID（外部キー） |

## 制約

1. **主キー**: `id`
2. **ユニーク制約**: `(candidate_id, platform)` - 同一プラットフォーム内での重複防止
3. **外部キー制約**:
   - `scraped_by` → `profiles(id)`
   - `client_id` → `clients(id)`
   - `requirement_id` → `job_requirements(id)`
   - `scraping_session_id` → `scraping_sessions(id)`

## インデックス

- `idx_candidates_candidate_id` - 候補者ID検索用
- `idx_candidates_platform` - プラットフォーム別検索用
- `idx_candidates_company` - 企業名検索用
- `idx_candidates_client` - クライアント別検索用
- `idx_candidates_requirement` - 要件別検索用
- `idx_candidates_session` - セッション別検索用
- `idx_candidates_scraped_at` - 日時順ソート用

## サンプルデータ

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "candidate_id": "1079961",
  "candidate_link": "https://cr-support.jp/resume/pdf?candidate=1079961",
  "candidate_company": "株式会社サンプル",
  "candidate_resume": "https://cr-support.jp/resume/pdf?candidate=1079961",
  "platform": "bizreach",
  "scraped_at": "2025-07-10T12:00:00Z",
  "scraped_by": "bb6f9acf-dd97-4b05-95a9-fac2e5390095",
  "client_id": "165ff0f4-8116-4e49-907b-69cf202a15f3",
  "requirement_id": "0c7ac90c-6851-4127-8bc6-c5a98f77b3de",
  "scraping_session_id": "456e7890-f012-34d5-b678-901234567890",
  "created_at": "2025-07-10T12:00:00Z",
  "updated_at": "2025-07-10T12:00:00Z"
}
```

## プラットフォーム別のcandidate_id形式

### Bizreach
- 形式: 数値文字列（例: "1079961"）
- 抽出元: URLパラメータ `candidate=XXXXXX`

### Green（将来対応）
- 形式: 英数字文字列
- 抽出元: プロフィールURL内のID

### Wantedly（将来対応）
- 形式: 数値または英数字
- 抽出元: ユーザーIDまたはプロフィールスラッグ

## 削除予定のカラム

以下のカラムは新構造では不要となるため、移行完了後に削除：

- name, email, phone（個人情報は別管理）
- bizreach_id, bizreach_url（汎用カラムに統合）
- current_title, current_position, current_company（簡略化）
- experience_years, skills, education（詳細情報は別管理）
- profile_url, profile_summary（candidate_linkに統合）
- scraped_data（正規化カラムに移行）
- その他の未使用カラム