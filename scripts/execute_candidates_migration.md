# Candidatesテーブル移行実行手順

## 実行日時: 2025-07-10

## 手順

### 1. Supabaseで以下のSQLを実行

`scripts/alter_candidates_table_final.sql`の内容をSupabase SQL Editorで実行してください。

### 2. 実行後の確認

以下のクエリで最終的なテーブル構造を確認：

```sql
-- テーブル構造の確認
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public' 
AND table_name = 'candidates'
AND column_name IN (
    'id', 'created_at', 'updated_at', 'platform',
    'candidate_id', 'candidate_link', 'candidate_company', 'candidate_resume',
    'scraped_at', 'scraped_by', 'client_id', 'requirement_id', 'scraping_session_id'
)
ORDER BY ordinal_position;

-- 制約の確認
SELECT
    tc.constraint_name,
    tc.constraint_type,
    kcu.column_name
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu 
    ON tc.constraint_name = kcu.constraint_name
WHERE tc.table_name = 'candidates'
ORDER BY tc.constraint_type, tc.constraint_name;
```

### 3. Chrome拡張機能の更新

次に以下のファイルを更新します：
- `/src/extension/content/scrapers/bizreach.js`
- `/src/extension/background/service-worker.js`
- `/src/web/routers/extension_api.py`

## 期待される結果

- 新しいカラムが追加される
- 既存データがある場合は適切に移行される
- 外部キー制約とインデックスが設定される
- ユニーク制約 `(candidate_id, platform)` が設定される