# Candidatesテーブル設計の改善案

## 現在の問題点

### 1. データの重複
- 同じ候補者が複数のスクレイピングセッションで取得される可能性
- `bizreach_id`で重複を排除する仕組みが必要

### 2. リレーションの不明確さ
- `scraped_data`フィールドにJSONで`client_id`や`requirement_id`を格納
- 正規化されていないため、クエリが複雑になる

### 3. スクレイピングセッションとの関連
- `session_id`がTEXT型で、`scraping_sessions`テーブルとの外部キー制約がない

## 改善案

### オプション1: 現在の構造を維持しつつ改善

```sql
-- candidatesテーブルの改善
ALTER TABLE candidates 
ADD CONSTRAINT unique_bizreach_id UNIQUE (bizreach_id);

-- インデックスの追加
CREATE INDEX idx_candidates_session_id ON candidates(session_id);
CREATE INDEX idx_candidates_bizreach_id ON candidates(bizreach_id);
CREATE INDEX idx_candidates_scraped_at ON candidates(scraped_at DESC);

-- scraped_dataからの検索を高速化
CREATE INDEX idx_candidates_scraped_data_client ON candidates((scraped_data->>'client_id'));
CREATE INDEX idx_candidates_scraped_data_requirement ON candidates((scraped_data->>'requirement_id'));
```

### オプション2: テーブル構造の正規化（推奨）

#### 1. candidate_profiles（候補者マスター）
```sql
CREATE TABLE candidate_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bizreach_id TEXT UNIQUE NOT NULL,
    name TEXT,
    email TEXT,
    phone TEXT,
    current_company TEXT,
    current_position TEXT,
    current_title TEXT,
    experience_years INTEGER,
    skills TEXT[],
    education TEXT,
    profile_summary TEXT,
    platform TEXT DEFAULT 'bizreach',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### 2. candidate_scraping_records（スクレイピング履歴）
```sql
CREATE TABLE candidate_scraping_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_profile_id UUID REFERENCES candidate_profiles(id),
    scraping_session_id UUID REFERENCES scraping_sessions(id),
    client_id UUID REFERENCES clients(id),
    requirement_id UUID REFERENCES job_requirements(id),
    bizreach_url TEXT,
    raw_html TEXT,
    parsed_data JSONB,
    scraped_at TIMESTAMPTZ DEFAULT NOW(),
    scraped_by UUID REFERENCES profiles(id)
);
```

### オプション3: 既存テーブルに正規化カラムを追加

```sql
-- candidatesテーブルに直接外部キーを追加
ALTER TABLE candidates 
ADD COLUMN client_id UUID REFERENCES clients(id),
ADD COLUMN requirement_id UUID REFERENCES job_requirements(id),
ADD COLUMN scraping_session_id UUID REFERENCES scraping_sessions(id);

-- scraped_dataから値を移行
UPDATE candidates 
SET 
    client_id = (scraped_data->>'client_id')::uuid,
    requirement_id = (scraped_data->>'requirement_id')::uuid
WHERE scraped_data IS NOT NULL;

-- インデックスの追加
CREATE INDEX idx_candidates_client_id ON candidates(client_id);
CREATE INDEX idx_candidates_requirement_id ON candidates(requirement_id);
CREATE INDEX idx_candidates_scraping_session_id ON candidates(scraping_session_id);
```

## 推奨事項

### 短期的対応（オプション3）
1. 既存のcandidatesテーブルに正規化カラムを追加
2. 外部キー制約とインデックスを設定
3. アプリケーションコードを徐々に移行

### 長期的対応（オプション2）
1. candidate_profilesとcandidate_scraping_recordsに分離
2. 候補者の基本情報と各スクレイピングの履歴を分離管理
3. より効率的なクエリとデータ管理が可能

## 実装手順

### Phase 1: 既存テーブルの改善
1. candidatesテーブルに正規化カラムを追加
2. 拡張機能のコードを更新して新しいカラムに値を設定
3. インデックスと制約を追加

### Phase 2: データ移行（オプション）
1. 既存のscraped_dataから新しいカラムへデータ移行
2. アプリケーションコードの更新
3. 古いJSONフィールドの廃止

### Phase 3: モニタリング
1. クエリパフォーマンスの監視
2. データ整合性の確認
3. 必要に応じて追加の最適化