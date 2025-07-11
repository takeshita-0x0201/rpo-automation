# Candidatesテーブル移行計画

## 現在の構造 → 新しい構造

### 維持するカラム
- `id` (UUID) - PRIMARY KEY
- `created_at` (TIMESTAMPTZ)
- `updated_at` (TIMESTAMPTZ)
- `platform` (TEXT) - デフォルト 'bizreach'
- `scraped_at` (TIMESTAMPTZ)
- `scraped_by` (TEXT/UUID)

### 新規追加/変更するカラム
| 現在のカラム | 新しいカラム | 説明 |
|------------|------------|------|
| bizreach_id | candidate_id | プラットフォーム共通の候補者ID |
| bizreach_url | candidate_link | プロフィールリンク |
| current_company | candidate_company | 所属企業名 |
| (新規) | candidate_resume | レジュメ情報/URL |

### リレーション正規化
| 現在 | 新規 | 説明 |
|------|------|------|
| scraped_data->>'client_id' | client_id (UUID) | 外部キー制約付き |
| scraped_data->>'requirement_id' | requirement_id (UUID) | 外部キー制約付き |
| session_id (TEXT) | scraping_session_id (UUID) | 外部キー制約付き |

## 移行手順

### Phase 1: カラム追加（破壊的変更なし）
```sql
-- 新しいカラムを追加
ALTER TABLE candidates 
ADD COLUMN IF NOT EXISTS candidate_id TEXT,
ADD COLUMN IF NOT EXISTS candidate_link TEXT,
ADD COLUMN IF NOT EXISTS candidate_company TEXT,
ADD COLUMN IF NOT EXISTS candidate_resume TEXT,
ADD COLUMN IF NOT EXISTS client_id UUID,
ADD COLUMN IF NOT EXISTS requirement_id UUID,
ADD COLUMN IF NOT EXISTS scraping_session_id UUID;
```

### Phase 2: アプリケーションコード更新
1. Chrome拡張機能の更新
   - 新しいカラムにデータを保存
   - 旧カラムへの保存も継続（互換性のため）

2. APIエンドポイントの更新
   - 新旧両方のカラムに値を設定
   - 読み取り時は新しいカラムを優先

### Phase 3: データ移行
```sql
-- 既存データを新しいカラムに移行
UPDATE candidates 
SET 
    candidate_id = COALESCE(bizreach_id, substring(bizreach_url from 'candidate=([0-9]+)')),
    candidate_link = COALESCE(bizreach_url, profile_url),
    candidate_company = current_company,
    client_id = (scraped_data->>'client_id')::uuid,
    requirement_id = (scraped_data->>'requirement_id')::uuid
WHERE candidate_id IS NULL;
```

### Phase 4: 制約とインデックス追加
```sql
-- NOT NULL制約
ALTER TABLE candidates 
ALTER COLUMN candidate_id SET NOT NULL,
ALTER COLUMN candidate_link SET NOT NULL;

-- 外部キー制約
ALTER TABLE candidates
ADD CONSTRAINT fk_candidates_client FOREIGN KEY (client_id) REFERENCES clients(id),
ADD CONSTRAINT fk_candidates_requirement FOREIGN KEY (requirement_id) REFERENCES job_requirements(id),
ADD CONSTRAINT fk_candidates_session FOREIGN KEY (scraping_session_id) REFERENCES scraping_sessions(id);

-- ユニーク制約
ALTER TABLE candidates 
ADD CONSTRAINT unique_candidate_per_platform UNIQUE (candidate_id, platform);
```

### Phase 5: 旧カラムの削除（オプション）
```sql
-- 全てのアプリケーションが新しいカラムを使用していることを確認後
ALTER TABLE candidates 
DROP COLUMN IF EXISTS bizreach_id,
DROP COLUMN IF EXISTS bizreach_url,
DROP COLUMN IF EXISTS current_company,
DROP COLUMN IF EXISTS name,
DROP COLUMN IF EXISTS email,
DROP COLUMN IF EXISTS phone,
DROP COLUMN IF EXISTS current_position,
DROP COLUMN IF EXISTS current_title,
DROP COLUMN IF EXISTS experience_years,
DROP COLUMN IF EXISTS skills,
DROP COLUMN IF EXISTS education,
DROP COLUMN IF EXISTS profile_url,
DROP COLUMN IF EXISTS profile_summary,
DROP COLUMN IF EXISTS scraped_data;
```

## コード変更例

### Chrome拡張機能 (content/scrapers/bizreach.js)
```javascript
// 旧形式（互換性のため維持）
const oldFormat = {
  bizreach_url: candidateUrl,
  bizreach_id: candidateId,
  current_company: companyName,
  // ... その他のフィールド
};

// 新形式
const newFormat = {
  candidate_id: candidateId,
  candidate_link: candidateUrl,
  candidate_company: companyName,
  candidate_resume: resumeUrl || resumeText,
  // メタデータ
  client_id: clientId,
  requirement_id: requirementId,
  scraping_session_id: sessionId
};

// 両方の形式を送信（移行期間中）
return { ...oldFormat, ...newFormat };
```

### API エンドポイント (extension_api.py)
```python
# 新旧両方のフィールドを処理
candidate_data = {
    # 新形式
    'candidate_id': candidate.candidate_id or candidate.bizreach_id,
    'candidate_link': candidate.candidate_link or candidate.bizreach_url,
    'candidate_company': candidate.candidate_company or candidate.current_company,
    'candidate_resume': candidate.candidate_resume,
    
    # リレーション
    'client_id': candidate.client_id or request.client_id,
    'requirement_id': candidate.requirement_id or request.requirement_id,
    'scraping_session_id': request.session_id,
    
    # 既存フィールド
    'scraped_by': current_user["id"],
    'platform': 'bizreach'
}
```

## タイムライン

1. **Week 1**: Phase 1-2 実施（カラム追加とコード更新）
2. **Week 2**: Phase 3 実施（データ移行）
3. **Week 3**: Phase 4 実施（制約追加）
4. **Week 4**: モニタリングと検証
5. **Month 2**: Phase 5 実施（旧カラム削除）