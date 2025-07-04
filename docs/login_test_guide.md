# ログイン機能テストガイド

## 1. WebAppの起動

```bash
./run_webapp.sh
```

## 2. Supabaseでのユーザーロール設定

1. Supabaseダッシュボードにログイン
2. SQL Editorを開く
3. 以下のSQLを実行してユーザーIDを確認：

```sql
-- 登録済みユーザーを確認
SELECT id, email FROM auth.users;
```

4. ユーザーIDをコピーして、以下のSQLでロールを設定：

```sql
-- adminロールを設定（YOUR-USER-IDを実際のIDに置き換え）
INSERT INTO profiles (id, role, full_name)
VALUES ('YOUR-USER-ID', 'admin', 'Admin User')
ON CONFLICT (id) 
DO UPDATE SET role = 'admin';

-- または通常ユーザーロールを設定
INSERT INTO profiles (id, role, full_name)
VALUES ('YOUR-USER-ID', 'user', 'Normal User')
ON CONFLICT (id) 
DO UPDATE SET role = 'user';
```

## 3. ログインテスト

1. ブラウザで http://localhost:8000 にアクセス
2. 自動的に `/login` にリダイレクトされます
3. Supabaseに登録したメールアドレスとパスワードでログイン
4. コンソールログを確認（ターミナルに表示されます）

### 期待される動作：
- `role = 'admin'` のユーザー → `/admin` ダッシュボードへリダイレクト
- `role = 'user'` のユーザー → `/user` ダッシュボードへリダイレクト
- ロールが未設定 → デフォルトで `/user` へリダイレクト

## 4. トラブルシューティング

### リダイレクトされない場合：

1. **ブラウザの開発者ツールを開く**
   - Network タブでリダイレクトレスポンスを確認
   - Console タブでJavaScriptエラーを確認

2. **ターミナルのログを確認**
   - `Login attempt for email: xxx`
   - `Login result: xxx`
   - `User role from DB: xxx`
   - `Redirecting to: xxx`

3. **Supabaseの確認**
   - profilesテーブルにユーザーのレコードが存在するか
   - roleカラムに正しい値が設定されているか

### よくある問題：

1. **"No profile found for user"**
   - profilesテーブルにユーザーIDに対応するレコードがない
   - 上記のSQL手順でプロファイルを作成してください

2. **ログイン後もログインページに戻る**
   - 認証エラーの可能性
   - メールアドレスとパスワードを確認

3. **404エラー**
   - `/admin` または `/user` ルートが正しく設定されていない
   - WebAppを再起動してみてください

## 5. ログアウト

ダッシュボード右上の「ログアウト」ボタンをクリックするか、直接 `/logout` にアクセス