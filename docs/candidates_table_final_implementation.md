# Candidatesテーブル最終実装

## 実施日: 2025-07-10

## 最終的なテーブル構造

### candidatesテーブル（13カラム）

```sql
CREATE TABLE candidates (
    -- 基本カラム (3)
    id UUID PRIMARY KEY,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,
    
    -- スクレイピングデータ (5)
    candidate_id TEXT NOT NULL,
    candidate_link TEXT NOT NULL,
    candidate_company TEXT,
    candidate_resume TEXT,
    platform TEXT NOT NULL DEFAULT 'bizreach',
    
    -- メタデータ (2)
    scraped_at TIMESTAMPTZ,
    scraped_by UUID,
    
    -- リレーション (3)
    client_id UUID NOT NULL,
    requirement_id UUID NOT NULL,
    scraping_session_id UUID
);
```

## 実装内容

### 1. データベース
- `create_candidates_table_clean.sql` - クリーンなテーブル作成SQL
- ユニーク制約: `(candidate_id, platform)`
- 外部キー制約: client_id, requirement_id, scraping_session_id
- RLSポリシー設定済み

### 2. Chrome拡張機能
- `/src/extension/content/scrapers/bizreach.js`
  - シンプルな4フィールド抽出
  - candidate_id自動生成ロジック
  - URLからのID抽出機能

### 3. APIエンドポイント
- `/src/web/routers/extension_api.py`
  - CandidateDataモデル（必須フィールドのみ）
  - クリーンな保存処理
  - 余分な変換ロジックを削除

## データフロー

```
Bizreachページ
    ↓
Chrome拡張機能（スクレイピング）
    ↓
{
  candidate_id: "1079961",
  candidate_link: "https://cr-support.jp/resume/pdf?candidate=1079961",
  candidate_company: "株式会社サンプル",
  candidate_resume: "https://cr-support.jp/resume/pdf?candidate=1079961",
  platform: "bizreach",
  client_id: "...",
  requirement_id: "...",
  scraping_session_id: "..."
}
    ↓
API（/api/extension/candidates/batch）
    ↓
Supabase candidatesテーブル
```

## 実行手順

1. **Supabaseでテーブル作成**
   ```
   create_candidates_table_clean.sql を実行
   ```

2. **Chrome拡張機能の動作確認**
   - 拡張機能を再読み込み
   - Bizreachで候補者一覧を開く
   - スクレイピングを実行

3. **データ確認**
   ```sql
   SELECT * FROM candidates ORDER BY created_at DESC LIMIT 10;
   ```

## 特徴

- **シンプル**: 必要最小限のカラムのみ
- **正規化**: リレーションは外部キーで管理
- **拡張性**: platformカラムで複数サイト対応可能
- **一意性**: candidate_id + platformで重複防止

## 今後の拡張案

1. **詳細情報テーブル**（必要に応じて）
   ```sql
   CREATE TABLE candidate_details (
       id UUID PRIMARY KEY,
       candidate_id UUID REFERENCES candidates(id),
       name TEXT,
       skills TEXT[],
       experience_details JSONB
   );
   ```

2. **他プラットフォーム対応**
   - Green: platform = 'green'
   - Wantedly: platform = 'wantedly'

3. **AI評価との連携**
   - ai_evaluations.candidate_id → candidates.id