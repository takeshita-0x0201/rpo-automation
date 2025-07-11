# Supabaseテーブル状況レポート

生成日時: 2025-07-10

## 概要

本レポートは、RPO自動化システムで使用するSupabaseのテーブルの現状を確認した結果をまとめたものです。

## テーブル存在確認結果

### ✅ 存在するテーブル（12個）

1. **profiles** - ユーザープロファイル
2. **clients** - クライアント企業
3. **job_requirements** - 採用要件マスター
4. **search_jobs** - 検索・AIマッチングジョブ
5. **job_status_history** - ジョブステータス履歴
6. **candidates** - 候補者マスター
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

**対応**: `scripts/create_missing_tables.sql`を作成しました。このSQLをSupabaseのSQLエディタで実行することで、不足しているテーブルを作成できます。

### 2. テーブル名の不一致

- **問題**: コードでは`jobs`テーブルを使用していますが、DATABASE_DESIGN.mdでは`search_jobs`として定義されています。
- **現状**: 両方のテーブルが存在しており、実際のコードでは`jobs`を使用しています。
- **推奨対応**: 
  - オプション1: `jobs`を正式なテーブル名として採用し、DATABASE_DESIGN.mdを更新
  - オプション2: コードを修正して`search_jobs`を使用するように変更

### 3. BigQueryからSupabaseへの移行状況

- WebAppとChrome拡張機能のBigQuery処理は全てSupabase処理に変更済み
- 環境変数からBigQuery関連の設定を削除済み
- 将来のBigQuery移行に備えて、依存関係は保持

## 次のステップ

1. **緊急度: 高**
   - Supabaseで`create_missing_tables.sql`を実行して不足テーブルを作成
   - `jobs`と`search_jobs`テーブルの統一方針を決定

2. **緊急度: 中**
   - DATABASE_DESIGN.mdを実際の実装に合わせて更新
   - テーブルのデータモデルの整合性確認

3. **緊急度: 低**
   - パフォーマンステストの実施
   - インデックスの最適化

## テーブル作成手順

1. Supabaseダッシュボードにログイン
2. SQL Editorを開く
3. `scripts/create_missing_tables.sql`の内容をコピー
4. SQLエディタに貼り付けて実行

## 確認コマンド

テーブルの存在確認を再度実行する場合：

```bash
# 仮想環境をアクティベート
source venv/bin/activate

# 確認スクリプトを実行
python scripts/check_supabase_tables.py
```