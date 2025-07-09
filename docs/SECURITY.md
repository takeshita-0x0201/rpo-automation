# セキュリティガイド

## セキュリティ設計の概要

本システムは、採用業務という機密性の高い情報を扱うため、複数層のセキュリティ対策を実装しています。

## Chrome拡張機能のセキュリティ

### 権限管理

| 項目 | 実装方法 |
|------|---------|
| APIキー管理 | Chrome Storage APIで暗号化保存 |
| 通信暗号化 | HTTPS必須、証明書ピンニング |
| トークン有効期限 | 1時間、自動リフレッシュ |
| Content Security Policy | 厳格なCSP設定 |

### manifest.json のセキュリティ設定

```json
{
    "content_security_policy": {
        "extension_pages": "script-src 'self'; object-src 'none'"
    },
    "permissions": [
        "storage",
        "activeTab"
    ],
    "host_permissions": [
        "https://*.bizreach.jp/*",
        "https://*.run.app/*"
    ]
}
```

### トークン管理のベストプラクティス

```javascript
// トークンの安全な保存
async function saveToken(token) {
    const encryptedToken = await encrypt(token);
    await chrome.storage.local.set({
        token: encryptedToken,
        expiry: Date.now() + TOKEN_LIFETIME
    });
}

// トークンの自動リフレッシュ
async function getValidToken() {
    const stored = await chrome.storage.local.get(['token', 'expiry']);
    
    if (Date.now() > stored.expiry - REFRESH_BUFFER) {
        return await refreshToken();
    }
    
    return await decrypt(stored.token);
}
```

## 環境別の認証情報管理

| 環境 | 管理方法 | 用途 |
|------|---------|-----|
| 開発環境 | .env.development | テストアカウントのみ使用 |
| Chrome拡張機能 | Chrome Storage API | JWTトークンのみ保存 |
| 本番Cloud | Secret Manager | 暗号化して保管、IAMで権限制御 |

### Secret Manager の設定

```bash
# シークレットの作成
gcloud secrets create api-key --data-file=api-key.txt

# アクセス権限の設定
gcloud secrets add-iam-policy-binding api-key \
    --member="serviceAccount:rpo-automation@project.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

## アクセス制御

### 最小権限の原則

各サービスアカウントは必要最小限の権限のみ付与：

```yaml
# Cloud Functions サービスアカウント
- bigquery.datasets.get
- bigquery.tables.get
- bigquery.tables.getData
- bigquery.tables.updateData
- secretmanager.versions.access
```

### 役職別アクセス制御

| 役職 | 権限 |
|------|------|
| operator | 自分の担当クライアントのみ |
| manager | 全クライアントの閲覧・実行 |
| admin | システム設定変更権限 |

### RLS (Row Level Security) の実装例

```sql
-- Supabaseでの実装例
CREATE POLICY "users_own_data" ON profiles
    FOR ALL USING (auth.uid() = id);

CREATE POLICY "admin_all_access" ON profiles
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM profiles
            WHERE id = auth.uid() AND role = 'admin'
        )
    );
```

## API セキュリティ

### JWT認証の実装

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials
    
    try:
        payload = jwt.decode(
            token, 
            SECRET_KEY, 
            algorithms=[ALGORITHM]
        )
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    
    return await get_user(user_id)
```

### CORS設定

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "chrome-extension://your-extension-id",
        "http://localhost:3000"  # 開発環境のみ
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)
```

### レート制限

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/candidates/batch")
@limiter.limit("100/hour")
async def receive_candidates_batch():
    # 処理
```

## データ保護

### 個人情報の暗号化

```python
from cryptography.fernet import Fernet

def encrypt_pii(data: str) -> str:
    """個人情報の暗号化"""
    f = Fernet(ENCRYPTION_KEY)
    return f.encrypt(data.encode()).decode()

def decrypt_pii(encrypted_data: str) -> str:
    """個人情報の復号化"""
    f = Fernet(ENCRYPTION_KEY)
    return f.decrypt(encrypted_data.encode()).decode()
```

### データマスキング

```python
def mask_email(email: str) -> str:
    """メールアドレスのマスキング"""
    local, domain = email.split('@')
    masked_local = local[0] + '*' * (len(local) - 2) + local[-1]
    return f"{masked_local}@{domain}"

def mask_name(name: str) -> str:
    """氏名のマスキング"""
    if len(name) <= 2:
        return name[0] + '*'
    return name[0] + '*' * (len(name) - 2) + name[-1]
```

## 監査とコンプライアンス

### ログ記録

すべてのAPI呼び出しをBigQuery audit_logsに記録：

```python
async def log_api_access(
    user_id: str,
    endpoint: str,
    method: str,
    ip_address: str,
    status_code: int
):
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "user_id": user_id,
        "endpoint": endpoint,
        "method": method,
        "ip_address": ip_address,
        "status_code": status_code
    }
    
    await bigquery_client.insert_rows_json(
        "system_logs.api_access_logs",
        [log_entry]
    )
```

### アクティビティ監視

```sql
-- 異常なアクセスパターンの検出
WITH user_activity AS (
    SELECT 
        user_id,
        COUNT(*) as request_count,
        COUNT(DISTINCT ip_address) as unique_ips,
        TIMESTAMP_DIFF(MAX(timestamp), MIN(timestamp), MINUTE) as duration_minutes
    FROM system_logs.api_access_logs
    WHERE timestamp > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)
    GROUP BY user_id
)
SELECT *
FROM user_activity
WHERE request_count > 1000 
   OR unique_ips > 5
   OR (request_count > 100 AND duration_minutes < 5)
```

## セキュリティチェックリスト

### 開発時

- [ ] 環境変数にハードコードされた認証情報がないか確認
- [ ] デバッグログに機密情報が出力されていないか確認
- [ ] 適切なエラーハンドリングが実装されているか確認

### デプロイ前

- [ ] すべての環境変数が Secret Manager に移行されているか
- [ ] HTTPS が有効になっているか
- [ ] CORS設定が本番環境用に更新されているか
- [ ] レート制限が適切に設定されているか

### 運用時

- [ ] 定期的なセキュリティアップデートの実施
- [ ] アクセスログの定期的な監査
- [ ] 異常なアクティビティの監視
- [ ] バックアップの定期的な確認

## インシデント対応

### 対応フロー

1. **検知**
   - アラート通知
   - ログ分析による異常検知

2. **初期対応**
   - 影響範囲の特定
   - 必要に応じてサービスの一時停止

3. **調査**
   - ログの詳細分析
   - 攻撃手法の特定

4. **復旧**
   - セキュリティパッチの適用
   - サービスの再開

5. **事後対応**
   - インシデントレポートの作成
   - 再発防止策の実施

### 緊急連絡先

- セキュリティチーム: security@company.com
- システム管理者: admin@company.com
- 外部セキュリティベンダー: vendor@security.com

## コンプライアンス

### 個人情報保護

- 個人情報は必要最小限のみ収集
- 暗号化による保護
- アクセス権限の厳格な管理
- 定期的なデータの削除

### 監査証跡

- すべての操作ログを90日間保持
- 改ざん防止のためのログの保護
- 定期的な監査レポートの作成

## セキュリティアップデート

### 依存関係の管理

```bash
# Pythonパッケージの脆弱性チェック
pip-audit

# npmパッケージの脆弱性チェック
npm audit

# 自動アップデート
dependabot または renovate の使用
```

### 定期的なセキュリティレビュー

- 月次でのコードレビュー
- 四半期ごとのペネトレーションテスト
- 年次でのセキュリティ監査