# Google Apps Script - クライアント評価アップローダー

## 概要

このGASスクリプトは、スプレッドシートの「候補者リスト」シートから、クライアント評価データを定期的にSupabaseのclient_evaluationsテーブルにアップロードします。

## ファイル構成

- `Code.gs` - 既存の候補者データ出力スクリプト（doPost用）
- `ClientEvaluationUploader.gs` - クライアント評価の定期アップロードスクリプト

## セットアップ手順

### 1. スクリプトプロパティの設定

```javascript
// GASエディタで実行
setupScriptProperties();
```

以下のプロパティを設定：
- `SPREADSHEET_ID` - 対象スプレッドシートのID（既存）
- `API_ENDPOINT` - FastAPIのエンドポイントURL
- `API_KEY` - API認証用のキー

### 2. 定期実行トリガーの設定

```javascript
// GASエディタで実行
setupTrigger();
```

1時間ごとに`syncClientEvaluations`関数が実行されます。

### 3. スプレッドシートの準備

「候補者リスト」シートに以下の列が必要：
- J列: Assigned HM (判断者)
- K列: Judgement / Meeting Type
- L列: Note
- Q列: Uploaded（アップロード済みフラグ）※自動追加

## 動作仕様

### アップロード条件

以下の条件をすべて満たす行がアップロード対象：
1. J列（Assigned HM）に値が入力されている
2. K列（Judgement）に値が入力されている
3. Q列（Uploaded）が空またはfalse

### 処理フロー

1. 定期実行（1時間ごと）でトリガー起動
2. 条件を満たす行を検出
3. FastAPIエンドポイントにJSON形式でPOST
4. 成功した行のQ列にタイムスタンプを記録

### 送信データ形式

```json
{
  "evaluations": [
    {
      "row_number": 2,
      "candidate_name": "候補者名",
      "candidate_company": "所属企業",
      "candidate_link": "プロフィールURL",
      "assigned_hm": "判断者名",
      "judgement": "評価結果",
      "note": "備考",
      "client_name": "クライアント名",
      "job_title": "求人タイトル",
      "evaluation_date": "2024-01-22T10:00:00.000Z"
    }
  ],
  "source": "google_sheets",
  "uploaded_at": "2024-01-22T10:00:00.000Z"
}
```

## テスト方法

### 手動テスト

```javascript
// GASエディタで実行（最初の3件のみ）
testSyncWithLimit();
```

### 本番実行

```javascript
// GASエディタで実行（全件処理）
syncClientEvaluations();
```

## トラブルシューティング

### エラーログの確認

GASエディタの「実行」→「実行履歴」からログを確認できます。

### よくある問題

1. **APIエンドポイントに接続できない**
   - スクリプトプロパティのAPI_ENDPOINTを確認
   - APIサーバーが起動しているか確認

2. **認証エラー**
   - API_KEYが正しく設定されているか確認
   - FastAPI側の認証設定を確認

3. **データがアップロードされない**
   - J列とK列に値が入力されているか確認
   - Q列が空であることを確認

## 注意事項

- 大量のデータがある場合、処理時間が長くなる可能性があります
- GASの実行時間制限（6分）に注意してください
- APIのレート制限を考慮して、必要に応じてバッチサイズを調整してください