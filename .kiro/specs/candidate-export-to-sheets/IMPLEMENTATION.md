# 候補者スプレッドシート出力機能 実装ガイド

## 概要

この機能は、AIマッチングシステムで評価された候補者を選択し、Google スプレッドシートに出力する機能です。

## 実装内容

### 1. データベース変更

#### マイグレーションファイル
- `/database/migrations/008_add_sent_to_sheet_fields.sql`
- `ai_evaluations`テーブルに以下のフィールドを追加：
  - `sent_to_sheet` (BOOLEAN): 送客済みフラグ
  - `sent_to_sheet_at` (TIMESTAMPTZ): 送客日時

### 2. バックエンドAPI

#### 修正ファイル
- `/webapp/routers/candidates.py`

#### 追加・修正内容
1. **候補者一覧表示API** (`job_candidates_list`)
   - 送客済み候補者数を統計情報に追加
   - 送客状態（`sent_to_sheet`）を含めて取得

2. **候補者エクスポートAPI** (`export_selected_candidates`)
   - エンドポイント: `POST /candidates/job/{job_id}/export-selected`
   - 選択された候補者のデータを整形
   - GAS webhookにPOSTリクエストを送信
   - 成功時に`ai_evaluations`テーブルの送客状態を更新

### 3. Google Apps Script (GAS)

#### ファイル
- `/.kiro/specs/candidate-export-to-sheets/gas/Code.gs`

#### 機能
- POSTリクエストを受け取り、スプレッドシートに新しいシートを作成
- 基本情報（送客日時、クライアント名、求人タイトルなど）を記載
- 候補者データを表形式で出力
- 自動フォーマット（列幅調整、罫線、条件付き書式）

### 4. フロントエンド

#### 修正ファイル
- `/webapp/templates/admin/job_candidates.html`

#### 追加・修正内容
1. **統計情報**
   - 送客済み候補者数の表示

2. **候補者一覧**
   - 送客済みバッジの表示

3. **JavaScript機能**
   - `exportToSheets()`関数の実装
   - スプレッドシートURL自動オープン機能
   - ページリロードによる送客状態の反映

## セットアップ手順

### 1. データベースマイグレーション

```bash
# Supabaseでマイグレーションを実行
supabase migration up
```

### 2. Google Apps Script のセットアップ

1. [Google Apps Script](https://script.google.com/) にアクセス
2. 新しいプロジェクトを作成
3. `Code.gs`の内容をコピー&ペースト
4. プロジェクトのプロパティで`SPREADSHEET_ID`を設定：
   ```javascript
   // Apps Script エディタで実行
   PropertiesService.getScriptProperties().setProperty('SPREADSHEET_ID', 'YOUR_SPREADSHEET_ID');
   ```
5. ウェブアプリとしてデプロイ：
   - デプロイ > 新しいデプロイ
   - 種類: ウェブアプリ
   - 実行ユーザー: 自分
   - アクセス権: 全員
6. デプロイ後のURLをコピー

### 3. 環境変数の設定

`.env`ファイルに以下を追加：

```bash
# 出力先スプレッドシートのエンドポイント
GAS_WEBHOOK_URL=https://script.google.com/macros/s/YOUR_SCRIPT_ID/exec
```

### 4. アプリケーションの再起動

```bash
# 開発環境
python webapp/main.py

# 本番環境
# Cloud Runの環境変数を更新してデプロイ
```

## 使用方法

1. 候補者一覧画面（`/job/{job_id}/candidates`）にアクセス
2. 送客したい候補者を選択（チェックボックス）
3. 「送客リストに追加」ボタンをクリック
4. 確認ダイアログで「OK」をクリック
5. 処理完了後、スプレッドシートが自動的に開く
6. ページがリロードされ、送客済みバッジが表示される

## トラブルシューティング

### GASエラーが発生する場合

1. スクリプトプロパティの`SPREADSHEET_ID`が正しく設定されているか確認
2. GASのアクセス権限が「全員」になっているか確認
3. スプレッドシートの共有設定を確認

### 送客済みバッジが表示されない場合

1. データベースマイグレーションが実行されているか確認
2. `ai_evaluations`テーブルに`sent_to_sheet`フィールドがあるか確認

### タイムアウトエラーが発生する場合

1. GASの実行時間制限（6分）を考慮し、大量の候補者を一度に送客しない
2. 必要に応じてバッチ処理を実装

## 今後の改善案

1. **バッチ処理**: 大量の候補者を分割して処理
2. **プログレスバー**: 処理進捗の可視化
3. **送客履歴画面**: 過去の送客履歴を確認できる画面
4. **テンプレート機能**: クライアントごとのスプレッドシートフォーマット
5. **エラーリトライ**: ネットワークエラー時の自動リトライ機能