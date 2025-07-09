# Chrome拡張機能ガイド

## 概要

本Chrome拡張機能は、Bizreachから候補者情報を効率的に収集し、クラウド上のAI判定システムと連携するためのツールです。セキュリティ制約によりPythonエージェントのインストールが困難な環境でも、ブラウザ拡張機能のみで動作します。

## 主な機能

1. **軽量インストール**: ブラウザ拡張機能のみで動作、Pythonランタイム不要
2. **リアルタイム連携**: FastAPIとの直接通信でリアルタイムな進捗表示
3. **セキュアな認証**: JWT認証でAPIアクセスを保護
4. **視覚的フィードバック**: スクレイピング中の進捗をブラウザ上で確認可能
5. **クライアント選択機能**: スクレイピング開始時にクライアントを選択

## プロジェクト構成

```
src/extension/
├── manifest.json            # 拡張機能の設定ファイル
├── background/              # バックグラウンドスクリプト
│   ├── service-worker.js    # メインのサービスワーカー
│   ├── api-client.js        # FastAPI通信クライアント
│   └── auth-manager.js      # 認証管理
├── content/                 # コンテンツスクリプト
│   ├── scraper.js           # Bizreachスクレイピングロジック
│   ├── ui-overlay.js        # 進捗表示UI
│   └── data-formatter.js    # データ整形
├── popup/                   # ポップアップUI
│   ├── popup.html           # ポップアップHTML
│   ├── popup.js             # ポップアップロジック
│   └── popup.css            # スタイル
└── shared/                  # 共通モジュール
    ├── constants.js         # 定数定義
    └── utils.js             # ユーティリティ関数
```

## インストール方法

### 開発版のインストール

1. **拡張機能のビルド**
```bash
# プロジェクトルートから実行
python scripts/build_extension.py

# または手動でファイルをコピー
cp -r src/extension/ dist/extension/
```

2. **Chromeへの読み込み**
   - Chromeで `chrome://extensions/` を開く
   - 右上の「デベロッパーモード」をONにする
   - 「パッケージ化されていない拡張機能を読み込む」をクリック
   - `dist/extension/` フォルダを選択

3. **初期設定**
   - 拡張機能アイコンを右クリック → 「オプション」
   - FastAPIエンドポイントURLを設定
     - 開発環境: `http://localhost:8000`
     - 本番環境: `https://your-api.run.app`

## 使用方法

### 1. 認証

1. 拡張機能アイコンをクリック
2. ログイン画面でRPOシステムの認証情報を入力
3. 「ログイン」ボタンをクリック
4. 認証成功後、JWTトークンが自動的に保存される

### 2. クライアント選択

1. Bizreachにログイン
2. 拡張機能のポップアップを開く
3. ドロップダウンから対象のクライアント企業を選択
4. 「選択」ボタンをクリック

### 3. 候補者情報の収集

1. Bizreachで検索条件を設定し、候補者一覧を表示
2. 拡張機能のポップアップで「スクレイピング開始」をクリック
3. 自動的に以下の処理が実行される：
   - 候補者一覧の取得
   - 各候補者の詳細ページへの遷移
   - 必要情報の抽出
   - FastAPIへのデータ送信
4. 進捗はブラウザ上にオーバーレイ表示される

### 4. 収集完了

- 全候補者の情報収集が完了すると通知が表示される
- 収集したデータ数と成功/失敗の内訳が確認できる
- データは自動的にBigQueryに保存される

## API連携

### 認証フロー

```javascript
// auth-manager.js の例
async function authenticate(email, password) {
    const response = await fetch(`${API_BASE_URL}/api/auth/extension/login`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ email, password })
    });
    
    const data = await response.json();
    if (data.access_token) {
        await chrome.storage.local.set({ 
            token: data.access_token,
            tokenExpiry: Date.now() + (30 * 60 * 1000) // 30分
        });
    }
    return data;
}
```

### データ送信

```javascript
// api-client.js の例
async function sendCandidateBatch(candidates, sessionId, clientId) {
    const token = await getStoredToken();
    
    const response = await fetch(`${API_BASE_URL}/api/candidates/batch`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
            candidates: candidates,
            session_id: sessionId,
            client_id: clientId
        })
    });
    
    return await response.json();
}
```

## スクレイピングロジック

### 候補者情報の抽出

```javascript
// scraper.js の例
function extractCandidateInfo() {
    const candidate = {
        name: document.querySelector('.candidate-name')?.textContent,
        company: document.querySelector('.current-company')?.textContent,
        position: document.querySelector('.current-position')?.textContent,
        experience: extractExperience(),
        skills: extractSkills(),
        education: extractEducation(),
        url: window.location.href,
        scraped_at: new Date().toISOString()
    };
    
    return candidate;
}

function extractSkills() {
    const skillElements = document.querySelectorAll('.skill-tag');
    return Array.from(skillElements).map(el => el.textContent.trim());
}
```

## セキュリティ設定

### manifest.json の権限設定

```json
{
    "manifest_version": 3,
    "name": "RPO Automation Extension",
    "version": "1.0.0",
    "permissions": [
        "storage",
        "activeTab",
        "scripting"
    ],
    "host_permissions": [
        "https://*.bizreach.jp/*",
        "http://localhost:8000/*",
        "https://*.run.app/*"
    ],
    "content_security_policy": {
        "extension_pages": "script-src 'self'; object-src 'none'"
    }
}
```

### トークン管理

- JWTトークンはChrome Storage APIで暗号化保存
- トークン有効期限は30分（自動リフレッシュ機能付き）
- ログアウト時は確実にトークンを削除

## トラブルシューティング

### よくある問題

#### 1. 拡張機能が表示されない
- デベロッパーモードが有効か確認
- manifest.jsonの構文エラーをチェック
- Chromeを再起動

#### 2. API接続エラー
- FastAPIサーバーが起動しているか確認
- エンドポイントURLが正しいか確認
- CORSエラーの場合はFastAPI側の設定を確認

#### 3. スクレイピングが途中で停止
- Bizreachのレート制限に引っかかっている可能性
- 待機時間を調整（constants.jsで設定）
- ネットワーク接続を確認

### デバッグ方法

1. **コンソールログの確認**
   - 拡張機能のポップアップ → 右クリック → 「検証」
   - バックグラウンドページ → chrome://extensions/ → 「サービスワーカー」をクリック

2. **ネットワークタブでAPI通信を確認**
   - リクエスト/レスポンスの内容を確認
   - ステータスコードとエラーメッセージを確認

3. **Chrome Storage の内容確認**
   ```javascript
   // コンソールで実行
   chrome.storage.local.get(null, (data) => console.log(data));
   ```

## 開発者向け情報

### ビルドプロセス

```python
# scripts/build_extension.py
import shutil
import json
import os

def build_extension():
    # 1. distディレクトリをクリーン
    if os.path.exists('dist/extension'):
        shutil.rmtree('dist/extension')
    
    # 2. ソースファイルをコピー
    shutil.copytree('src/extension', 'dist/extension')
    
    # 3. 環境別の設定を適用
    env = os.getenv('BUILD_ENV', 'development')
    update_manifest_for_env(env)
    
    print(f"Extension built for {env} environment")
```

### テスト方法

1. **ユニットテスト**
   ```bash
   npm test
   ```

2. **E2Eテスト**
   - Puppeteerを使用した自動テスト
   - テストアカウントでの動作確認

### リリース手順

1. バージョン番号の更新（manifest.json）
2. 本番環境用にビルド
3. Chrome Web Storeへのアップロード
4. 社内配布の場合は.crxファイルを生成

## ベストプラクティス

### パフォーマンス最適化

1. **バッチ処理**
   - 候補者データは10件ずつバッチで送信
   - メモリ使用量を抑制

2. **非同期処理**
   - Promise.allを使用した並列処理
   - 適切なエラーハンドリング

3. **キャッシュの活用**
   - 頻繁にアクセスするデータはメモリにキャッシュ
   - Chrome Storage APIの使用を最小限に

### エラーハンドリング

```javascript
// エラーハンドリングの例
async function safeScraping() {
    try {
        const data = await extractCandidateInfo();
        await sendToAPI(data);
    } catch (error) {
        console.error('Scraping error:', error);
        await logError(error);
        showUserNotification('エラーが発生しました。詳細はログを確認してください。');
    }
}
```

### ユーザビリティ

1. **進捗表示**
   - リアルタイムで処理状況を表示
   - 残り時間の推定表示

2. **エラー通知**
   - ユーザーフレンドリーなエラーメッセージ
   - 解決方法の提示

3. **設定の保存**
   - ユーザー設定はローカルに保存
   - 次回起動時に自動復元