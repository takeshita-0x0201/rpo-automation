# Edge Function デプロイ手順

## 1. Supabase CLI のインストール

```bash
npm install -g supabase
```

## 2. プロジェクトにリンク

```bash
supabase link --project-ref your-project-ref
```

## 3. 環境変数の設定

```bash
# Edge Function シークレットを設定
supabase secrets set GEMINI_API_KEY=your_gemini_api_key
supabase secrets set TAVILY_API_KEY=your_tavily_api_key
```

## 4. Edge Function のデプロイ

```bash
# 関数をデプロイ
supabase functions deploy process-matching

# 確認
supabase functions list
```

## 5. データベースマイグレーション

```bash
# マイグレーションを実行
supabase db push
```

## 6. FastAPI アプリケーションの環境変数

`.env` ファイルに追加:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
```

## 7. 動作確認

1. ジョブ管理画面から候補者を選択
2. 「AIマッチングを実行」ボタンをクリック
3. 進捗状況を確認
4. 完了後、結果を確認

## トラブルシューティング

### Edge Function がタイムアウトする場合

Edge Function は最大実行時間が 150 秒なので、処理を分割することを検討:

```typescript
// 長時間処理を複数のステップに分割
async function processInSteps(jobId: string) {
  await processStep1(jobId)
  await processStep2(jobId)
  await processStep3(jobId)
}
```

### CORS エラーが発生する場合

Edge Function に CORS ヘッダーを追加:

```typescript
return new Response(JSON.stringify(result), {
  headers: {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
  },
})
```