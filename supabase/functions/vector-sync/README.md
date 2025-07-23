# Vector Sync Edge Function

client_evaluationsテーブルからPineconeへのベクトル同期を行うEdge Function。

## セットアップ

### 1. 環境変数の設定

Supabaseダッシュボードで以下のシークレットを設定：

```bash
supabase secrets set GEMINI_API_KEY="your_gemini_api_key"
supabase secrets set PINECONE_API_KEY="your_pinecone_api_key" 
supabase secrets set PINECONE_INDEX_HOST="recruitment-matching-xxxxxx.svc.gcp-starter.pinecone.io"
```

### 2. デプロイ

```bash
supabase functions deploy vector-sync
```

### 3. 定期実行の設定

Supabaseのcronジョブで定期実行を設定：

```sql
-- 1時間ごとに実行
SELECT
  cron.schedule(
    'vector-sync-hourly',
    '0 * * * *', -- 毎時0分
    $$
    SELECT
      net.http_post(
        url:='https://agpoeoexuirxzdszdtlu.supabase.co/functions/v1/vector-sync',
        headers:='{"Authorization": "Bearer ' || current_setting('app.settings.service_role_key') || '"}'::jsonb
      ) AS request_id;
    $$
  );
```

## 動作確認

### 手動実行

```bash
# ローカルテスト
supabase functions serve vector-sync --env-file ./supabase/functions/vector-sync/.env

# 本番実行
curl -i --location --request POST \
  'https://agpoeoexuirxzdszdtlu.supabase.co/functions/v1/vector-sync' \
  --header 'Authorization: Bearer YOUR_ANON_KEY' \
  --header 'Content-Type: application/json'
```

### レスポンス例

```json
{
  "processed": 5,
  "success": 4,
  "failed": 1,
  "errors": [
    {
      "candidate_id": "山田太郎",
      "error": "Required field missing: job_description"
    }
  ]
}
```

## 処理フロー

1. `synced_to_pinecone = false`のレコードを最大5件取得
2. 各レコードについて：
   - 関連データ（候補者、求人、AI評価）を収集
   - 3種類のベクトル（combined、job_side、candidate）を生成
   - Gemini APIでエンベディング化
   - Pineconeに保存
   - `synced_to_pinecone = true`に更新
3. エラーの場合は`sync_error`に記録

## レート制限

- Gemini無料枠: 15 RPM、1500/日
- 1実行あたり最大5件処理（15リクエスト = 5件 × 3ベクトル）
- 各エンベディング生成後に4秒待機

## トラブルシューティング

### よくあるエラー

1. **"Required field missing"**
   - 必須フィールド（job_description、memo、candidate_resume等）が欠けている
   - 対象データを確認して補完が必要

2. **"Gemini API rate limit"**
   - レート制限に達した
   - BATCH_SIZEを減らすか、実行間隔を長くする

3. **"Pinecone connection error"**
   - PINECONE_INDEX_HOSTが正しいか確認
   - API Keyが有効か確認

### ログの確認

```bash
supabase functions logs vector-sync
```