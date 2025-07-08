# データベース設計ドキュメント

## 概要
RPO Automationシステムのデータベース設計と管理に関するドキュメントです。

## テーブル構造

### 1. profiles（ユーザープロファイル）
- **既存テーブル**
- ユーザーの基本情報とロール管理

### 2. clients（クライアント企業）
- **既存テーブル**
- クライアント企業の情報管理

### 3. requirements（採用要件）
- **新規テーブル**
- クライアントごとの採用要件を管理
- ポジション情報、必要スキル、給与レンジなど

### 4. candidates（候補者）
- **新規テーブル**
- 候補者の情報を一元管理
- 外部システムから取得したデータを統合

### 5. search_jobs（検索ジョブ）
- **新規テーブル**
- 検索処理の実行履歴と状態管理
- バックグラウンドジョブの追跡

### 6. search_results（検索結果）
- **新規テーブル**
- 検索ジョブと候補者のマッチング結果
- スコアリングとレビュー状態の管理

## セットアップ手順

### 1. Supabaseダッシュボードでの作業

1. [Supabase Dashboard](https://app.supabase.com)にログイン
2. 該当プロジェクトを選択
3. 左側メニューから「SQL Editor」を選択
4. 新しいクエリを作成

### 2. テーブル作成

以下の順序でSQLを実行してください：

```sql
-- 1. UUID拡張を有効化（まだの場合）
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. migrations/001_create_core_tables.sql の内容を実行
```

### 3. 初期データ投入（オプション）

開発用のサンプルデータが必要な場合：

```sql
-- サンプル採用要件
INSERT INTO requirements (
    client_id,
    position_name,
    description,
    required_skills,
    preferred_skills,
    experience_years_min,
    experience_years_max,
    salary_min,
    salary_max,
    location,
    status
) VALUES (
    (SELECT id FROM clients LIMIT 1),
    'シニアバックエンドエンジニア',
    'マイクロサービスアーキテクチャの設計・開発をリードしていただきます。',
    ARRAY['Python', 'Django', 'PostgreSQL', 'Docker'],
    ARRAY['Kubernetes', 'AWS', 'GraphQL'],
    5,
    10,
    8000000,
    12000000,
    '東京都',
    'active'
);

-- サンプル候補者
INSERT INTO candidates (
    external_id,
    source,
    profile_data,
    skills,
    experience_years,
    current_position,
    location
) VALUES (
    'sample_001',
    'manual',
    '{"summary": "10年以上の開発経験を持つエンジニア"}',
    ARRAY['Python', 'Django', 'React', 'AWS'],
    10,
    'リードエンジニア',
    '東京都'
);
```

## データモデルの特徴

### 1. 柔軟性
- `profile_data`と`search_criteria`にJSONB型を使用
- 外部システムの多様なデータ形式に対応

### 2. パフォーマンス
- 適切なインデックスの設定
- GINインデックスによる配列検索の最適化

### 3. セキュリティ
- Row Level Security (RLS)の実装
- ロールベースのアクセス制御

### 4. 監査性
- created_at/updated_atの自動管理
- 作成者・更新者の記録

## 注意事項

1. **外部キー制約**
   - ON DELETE CASCADEが設定されているため、親レコード削除時は注意

2. **一意制約**
   - candidates: (external_id, source)のペアで一意
   - search_results: (search_job_id, candidate_id)のペアで一意

3. **データ型**
   - 金額は円単位の整数型
   - スキルは文字列の配列型
   - 詳細データはJSONB型

## トラブルシューティング

### よくあるエラー

1. **UUID拡張が有効化されていない**
   ```
   ERROR: function uuid_generate_v4() does not exist
   ```
   解決: `CREATE EXTENSION IF NOT EXISTS "uuid-ossp";`を実行

2. **外部キー制約違反**
   ```
   ERROR: insert or update on table "requirements" violates foreign key constraint
   ```
   解決: 参照先のレコードが存在することを確認

3. **権限エラー**
   ```
   ERROR: permission denied for table
   ```
   解決: RLSポリシーを確認、またはservice_role_keyを使用