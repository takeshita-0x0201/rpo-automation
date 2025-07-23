# Supabaseのキーを取得する方法

## 手順

1. **Supabaseダッシュボードにアクセス**
   - https://supabase.com/dashboard/project/agpoeoexuirxzdszdtlu

2. **Settings → API に移動**
   - 左側メニューの「Settings」をクリック
   - 「API」セクションを選択

3. **必要なキーをコピー**
   - **anon key** (public): 公開可能なキー
   - **service_role key** (secret): 管理者権限のキー（秘密にすること）

4. **Edge Functionのテストで使用**
   - service_role keyを使用してテスト実行

## curlコマンドでのテスト方法

```bash
# service_role keyを使用
curl -X POST https://agpoeoexuirxzdszdtlu.supabase.co/functions/v1/vector-sync \
  -H "Authorization: Bearer YOUR_SERVICE_ROLE_KEY" \
  -H "Content-Type: application/json" \
  -d '{}'
```

## 注意事項
- service_role keyは管理者権限を持つため、本番環境では絶対に公開しないこと
- GitHubなどにコミットしないよう注意