# BigQuery セットアップガイド

## 概要
このガイドでは、RPO AutomationのBigQuery環境をセットアップする手順を説明します。

## 前提条件
- Google Cloud Projectへのアクセス権限
- BigQueryの管理者権限
- プロジェクトID: `rpo-automation`

## セットアップ手順

### 1. BigQuery構成の確認

まず、現在のBigQuery環境の状態を確認します。

```bash
# BigQuery コンソールにアクセス
https://console.cloud.google.com/bigquery
```

`/bigquery/check_structure.sql` のクエリを順番に実行して、以下を確認：
- データセットの存在
- テーブルの存在
- カラム構造
- データの有無

### 2. テーブルが存在しない場合

`/bigquery/verify_table_existence.sql` を使用して：

1. **簡易確認**
   ```sql
   SELECT COUNT(*) as table_exists FROM `rpo-automation.recruitment_data.candidates` LIMIT 1;
   ```
   エラーが出る場合、テーブルが存在しません。

2. **データセット作成**
   ```sql
   CREATE SCHEMA IF NOT EXISTS `rpo-automation.recruitment_data`
   OPTIONS(
     description="RPO Automation - 採用候補者データ",
     location="asia-northeast1"
   );
   ```

3. **テーブル作成**
   - verify_table_existence.sql の CREATE TABLE 文を実行

### 3. テーブル構造の確認

作成されたテーブルの構造：

#### candidatesテーブル
| カラム名 | データ型 | 説明 |
|---------|----------|------|
| id | STRING | 候補者の一意ID |
| search_id | STRING | 検索セッションID |
| session_id | STRING | スクレイピングセッションID |
| name | STRING | 候補者名 |
| current_company | STRING | 現在の会社 |
| current_position | STRING | 現在の役職 |
| experience_years | INT64 | 経験年数 |
| skills | ARRAY<STRING> | スキル一覧 |
| scraped_at | TIMESTAMP | スクレイピング日時 |
| scraped_data | JSON | 追加データ（client_id含む） |

### 4. 権限設定

サービスアカウントに必要な権限：
- `bigquery.dataViewer` - データ読み取り
- `bigquery.dataEditor` - データ書き込み
- `bigquery.jobUser` - クエリ実行

```bash
# サービスアカウントへの権限付与例
gcloud projects add-iam-policy-binding rpo-automation \
  --member="serviceAccount:YOUR_SERVICE_ACCOUNT@rpo-automation.iam.gserviceaccount.com" \
  --role="roles/bigquery.dataEditor"
```

### 5. 環境変数の設定

アプリケーションで使用する環境変数：

```bash
# .env ファイル
GOOGLE_CLOUD_PROJECT=rpo-automation
BIGQUERY_DATASET_ID=recruitment_data
BIGQUERY_TABLE_ID=candidates

# 認証情報（どちらか一方）
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
# または
GOOGLE_APPLICATION_CREDENTIALS_JSON={"type":"service_account",...}
```

### 6. 動作確認

1. **サンプルデータの挿入**
   ```sql
   -- verify_table_existence.sql のサンプルデータ挿入SQLを実行
   ```

2. **候補者数カウントのテスト**
   ```sql
   SELECT COUNT(DISTINCT id) as count
   FROM `rpo-automation.recruitment_data.candidates`
   WHERE scraped_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY);
   ```

3. **アプリケーションからの接続テスト**
   - ジョブ一覧画面で「対象数」が表示されることを確認

## トラブルシューティング

### エラー: "Table not found"
- データセットとテーブルが作成されているか確認
- プロジェクトIDが正しいか確認

### エラー: "Permission denied"
- サービスアカウントの権限を確認
- 認証情報が正しく設定されているか確認

### エラー: "取得エラー"と表示される
- BigQueryへの接続を確認
- ログでエラー詳細を確認
- scraped_data内にclient_idが含まれているか確認

## コスト管理

### 推奨設定
- パーティション有効期限: 180日（6ヶ月）
- クラスタリング: search_id, current_company
- 必要に応じて古いパーティションを手動削除

### 料金見積もり
- ストレージ: $0.02/GB/月
- クエリ: $5/TB（最初の1TBは無料）
- 月間推定: 約$10-50（使用量による）

## 次のステップ

1. Chrome拡張機能でデータ収集を開始
2. ジョブを作成して候補者数を確認
3. AIマッチング機能の実装へ進む