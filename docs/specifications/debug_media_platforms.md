# Chrome拡張機能 媒体プラットフォーム表示問題のデバッグ手順

## 問題
Chrome拡張機能で媒体プラットフォームが表示されない

## デバッグ手順

### 1. APIエンドポイントの直接確認
ブラウザで以下のURLにアクセスして、データが返されるか確認：
```
http://localhost:8000/api/media_platforms
```

期待される応答：
```json
{
  "success": true,
  "platforms": [
    {
      "id": "...",
      "name": "bizreach",
      "display_name": "ビズリーチ",
      "url_patterns": ["cr-support.jp", "bizreach.jp"],
      "is_active": true,
      "sort_order": 1
    },
    // ... 他のプラットフォーム
  ]
}
```

### 2. Supabaseデータベースの確認

Supabaseダッシュボードで以下を確認：

1. `media_platforms`テーブルが存在するか
2. テーブルにデータが入っているか
3. RLSポリシーが正しく設定されているか

SQLクエリで確認：
```sql
-- テーブルの存在確認
SELECT * FROM media_platforms ORDER BY sort_order;

-- RLSポリシーの確認
SELECT * FROM pg_policies WHERE tablename = 'media_platforms';
```

### 3. Chrome拡張機能のコンソールログ確認

1. Chrome拡張機能の管理ページを開く（chrome://extensions/）
2. RPO Automation拡張機能の「サービスワーカー」をクリック
3. コンソールで以下を確認：
   - `GET_MEDIA_PLATFORMS`メッセージが送信されているか
   - APIレスポンスにエラーがないか

### 4. ネットワークタブでの確認

1. Chrome DevToolsを開く（F12）
2. Networkタブを選択
3. 拡張機能のポップアップを開く
4. `/api/media_platforms`へのリクエストを確認：
   - ステータスコード
   - レスポンス内容
   - エラーメッセージ

## 考えられる原因と解決策

### 原因1: データベースにテーブルまたはデータが存在しない

**解決策**: 以下のSQLを実行
```bash
# Supabaseに接続してSQLを実行
psql -h <SUPABASE_HOST> -U postgres -d postgres < database/scripts/create_media_platforms_table.sql
psql -h <SUPABASE_HOST> -U postgres -d postgres < database/scripts/add_url_patterns_to_media_platforms.sql
```

### 原因2: RLSポリシーによるアクセス制限

**解決策**: RLSポリシーを確認し、必要に応じて修正
```sql
-- 全ユーザーが媒体一覧を閲覧可能にする
DROP POLICY IF EXISTS "Everyone can view media platforms" ON media_platforms;
CREATE POLICY "Everyone can view media platforms" ON media_platforms
    FOR SELECT
    USING (true);
```

### 原因3: APIの認証エラー

**解決策**: 
1. Chrome拡張機能で再ログイン
2. トークンの有効期限を確認
3. APIエンドポイントの認証設定を確認

### 原因4: CORS設定の問題

**解決策**: FastAPIのCORS設定を確認（webapp/main.py）
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["chrome-extension://*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 追加の確認事項

1. **Supabase接続設定**
   - 環境変数 `SUPABASE_URL` と `SUPABASE_KEY` が正しく設定されているか
   - `core/utils/supabase_client.py` で接続が成功しているか

2. **拡張機能のmanifest.json**
   - 必要な権限（`storage`, `tabs`, `http://localhost:8000/*`）が設定されているか

3. **開発サーバーの起動**
   - FastAPIサーバーが起動しているか（`python run_webapp.py`）
   - ポート8000でアクセス可能か

## テスト用スクリプト

以下のPythonスクリプトで直接APIをテスト：

```python
import requests

# APIエンドポイントをテスト
response = requests.get("http://localhost:8000/api/media_platforms")
print(f"Status Code: {response.status_code}")
print(f"Response: {response.json()}")
```

## ログの確認場所

1. **FastAPIログ**: ターミナルでサーバー実行時の出力
2. **Chrome拡張機能ログ**: chrome://extensions/ → サービスワーカー → コンソール
3. **Supabaseログ**: Supabaseダッシュボード → Logs