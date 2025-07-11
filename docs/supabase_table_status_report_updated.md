# Supabaseテーブル状況レポート（更新版）

生成日時: 2025-07-10

## 概要

本レポートは、RPO自動化システムで使用するSupabaseのテーブルの現状を確認した結果をまとめたものです。

## 重要な発見事項

### ID型の不一致

既存のテーブルでは、IDカラムの型が**TEXT型**で統一されています：
- `profiles.id`: TEXT型
- `clients.id`: TEXT型
- `job_requirements.id`: TEXT型
- `candidates.id`: TEXT型

これは、DATABASE_DESIGN.mdで定義されているUUID型とは異なります。

## テーブル存在確認結果

### ✅ 存在するテーブル（12個）

1. **profiles** - ユーザープロファイル（id: TEXT型）
2. **clients** - クライアント企業（id: TEXT型）
3. **job_requirements** - 採用要件マスター（id: TEXT型）
4. **search_jobs** - 検索・AIマッチングジョブ
5. **job_status_history** - ジョブステータス履歴
6. **candidates** - 候補者マスター（id: TEXT型）
7. **candidate_submissions** - 候補者データ提出履歴
8. **search_results** - 検索結果
9. **notification_settings** - 通知設定
10. **retry_queue** - リトライキュー
11. **scraping_sessions** - スクレイピングセッション
12. **jobs** - ジョブ管理（DATABASE_DESIGN.mdに定義なし）

### ❌ 存在しないテーブル（3個）

1. **client_settings** - クライアント別設定
2. **ai_evaluations** - AI評価結果
3. **searches** - 検索セッション

## 問題点と対応

### 1. 不足しているテーブル

以下の3つのテーブルが不足しています：
- `client_settings`
- `ai_evaluations`
- `searches`

**対応**: 
- ❌ `scripts/create_missing_tables.sql` - UUID型で作成（エラー発生）
- ✅ `scripts/create_missing_tables_fixed.sql` - TEXT型で修正済み

### 2. テーブル名の不一致

- **問題**: コードでは`jobs`テーブルを使用していますが、DATABASE_DESIGN.mdでは`search_jobs`として定義されています。
- **現状**: 両方のテーブルが存在しており、実際のコードでは`jobs`を使用しています。
- **推奨対応**: 
  - オプション1: `jobs`を正式なテーブル名として採用し、DATABASE_DESIGN.mdを更新
  - オプション2: コードを修正して`search_jobs`を使用するように変更

### 3. ID型の不一致

- **問題**: DATABASE_DESIGN.mdではUUID型として定義されていますが、実際のテーブルではTEXT型が使用されています。
- **影響**: 外部キー制約の設定時に型の不一致エラーが発生
- **対応**: 新規テーブル作成時は既存のTEXT型に合わせる必要があります

### 4. BigQueryからSupabaseへの移行状況

- ✅ WebAppとChrome拡張機能のBigQuery処理は全てSupabase処理に変更済み
- ✅ 環境変数からBigQuery関連の設定を削除済み
- ✅ 将来のBigQuery移行に備えて、依存関係は保持

## 次のステップ

1. **緊急度: 高**
   - Supabaseで`create_missing_tables_fixed.sql`を実行して不足テーブルを作成
   - `jobs`と`search_jobs`テーブルの統一方針を決定

2. **緊急度: 中**
   - DATABASE_DESIGN.mdを実際の実装に合わせて更新（特にID型をTEXTに変更）
   - テーブルのデータモデルの整合性確認

3. **緊急度: 低**
   - パフォーマンステストの実施
   - インデックスの最適化

## テーブル作成手順

1. Supabaseダッシュボードにログイン
2. SQL Editorを開く
3. **`scripts/create_missing_tables_fixed.sql`**の内容をコピー（型修正版を使用）
4. SQLエディタに貼り付けて実行

## 型情報確認クエリ

既存テーブルの型を確認する場合：

```sql
SELECT 
    table_name,
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public' 
AND table_name IN ('profiles', 'clients', 'job_requirements', 'candidates', 'search_jobs', 'jobs')
ORDER BY table_name, ordinal_position;
```

## 確認コマンド

テーブルの存在確認を再度実行する場合：

```bash
# 仮想環境をアクティベート
source venv/bin/activate

# 確認スクリプトを実行
python scripts/check_supabase_tables.py

# 型情報を確認
python scripts/check_table_types.py
```