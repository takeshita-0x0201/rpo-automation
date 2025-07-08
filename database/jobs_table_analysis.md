# jobsテーブル分析

## 現在のjobsテーブル構造

```
カラム:
- id (uuid)
- requirement_id (text) - 採用要件との関連
- client_id (uuid) - クライアントとの関連
- status (text) - ジョブのステータス
- created_by (uuid) - 作成者
- created_at (timestamptz) - 作成日時
- updated_at (timestamptz) - 更新日時
```

## 分析結果

### ✅ search_jobsの代替として機能している点

1. **requirement_idカラムが存在**
   - 採用要件との関連付けが可能
   - ただし、データ型がtextなので要注意

2. **基本的な追跡機能**
   - status: ジョブの状態管理
   - created_by: 誰が実行したか
   - タイムスタンプ: いつ実行されたか

3. **client_idで直接クライアント参照**
   - requirementを経由せずにクライアントを特定可能

### ⚠️ 不足している可能性がある機能

設計したsearch_jobsと比較して不足している項目：

```sql
-- search_jobsにあってjobsにない項目
- search_criteria (JSONB) -- 検索条件の詳細
- progress (INTEGER) -- 進捗状況（0-100%）
- started_at (TIMESTAMPTZ) -- 実際の開始時刻
- completed_at (TIMESTAMPTZ) -- 完了時刻
- total_results (INTEGER) -- 総結果数
- matched_results (INTEGER) -- マッチした結果数
- error_message (TEXT) -- エラー詳細
- execution_time_seconds (INTEGER) -- 実行時間
```

## 💡 推奨アプローチ

### Option 1: jobsテーブルを拡張（推奨）
既存のjobsテーブルに必要なカラムを追加：

```sql
-- jobsテーブルの拡張
ALTER TABLE jobs 
ADD COLUMN IF NOT EXISTS search_criteria JSONB,
ADD COLUMN IF NOT EXISTS progress INTEGER DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
ADD COLUMN IF NOT EXISTS started_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS total_results INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS matched_results INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS error_message TEXT;

-- requirement_idの型を修正（もしUUIDにしたい場合）
-- 注意: 既存データがある場合は変換が必要
-- ALTER TABLE jobs ALTER COLUMN requirement_id TYPE UUID USING requirement_id::UUID;
```

### Option 2: そのまま使用
現状のjobsテーブルでも基本的な機能は実現可能：
- ジョブの作成・追跡
- ステータス管理
- 履歴の保持

詳細な情報はjob_status_historyテーブルに記録する設計かもしれません。

## 🔍 確認すべきポイント

1. **requirement_idがtextである理由**
   - 外部システムのIDを格納？
   - UUID以外の形式を許容？

2. **job_status_historyの役割**
   - 詳細な実行ログはこちらに保存？
   - progressやerror_messageはこちらで管理？

3. **検索条件の保存場所**
   - requirementsテーブルに保存？
   - 別途search_criteriaテーブルが存在？