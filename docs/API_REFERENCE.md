# API リファレンス

## 概要

本システムのFastAPIは、Chrome拡張機能と各種バックエンドサービスを統合するAPI統合ハブとして機能します。

## ベースURL

- 開発環境: `http://localhost:8000`
- 本番環境: `https://your-api.run.app`

## 認証

すべてのAPIエンドポイント（認証エンドポイントを除く）はJWT認証が必要です。

```http
Authorization: Bearer <your-jwt-token>
```

## エンドポイント一覧

### 認証関連

#### POST /api/auth/extension/login
Chrome拡張機能用のログインエンドポイント

**リクエスト:**
```json
{
    "email": "user@example.com",
    "password": "password123"
}
```

**レスポンス:**
```json
{
    "access_token": "eyJhbGciOiJS...",
    "token_type": "bearer",
    "user": {
        "id": "uuid",
        "email": "user@example.com",
        "role": "user",
        "full_name": "山田太郎"
    }
}
```

#### POST /api/auth/refresh
トークンのリフレッシュ

**リクエスト:**
```json
{
    "refresh_token": "eyJhbGciOiJS..."
}
```

**レスポンス:**
```json
{
    "access_token": "eyJhbGciOiJS...",
    "token_type": "bearer"
}
```

### クライアント管理

#### GET /api/clients
クライアント一覧の取得

**クエリパラメータ:**
- `active_only`: `true` でアクティブなクライアントのみ取得（デフォルト: `false`）
- `page`: ページ番号（デフォルト: 1）
- `per_page`: 1ページあたりの件数（デフォルト: 20）

**レスポンス:**
```json
{
    "clients": [
        {
            "id": "uuid",
            "name": "株式会社A",
            "industry": "IT",
            "size": "100-500名",
            "is_active": true
        }
    ],
    "total": 50,
    "page": 1,
    "per_page": 20
}
```

#### GET /api/clients/{client_id}
特定クライアントの詳細取得

**レスポンス:**
```json
{
    "id": "uuid",
    "name": "株式会社A",
    "industry": "IT",
    "size": "100-500名",
    "contact_person": "採用担当",
    "contact_email": "recruit@company-a.com",
    "bizreach_search_url": "https://bizreach.jp/...",
    "is_active": true,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
}
```

### 候補者データ管理

#### POST /api/candidates/batch
候補者データのバッチ送信

**リクエスト:**
```json
{
    "candidates": [
        {
            "name": "候補者A",
            "email": "candidate-a@example.com",
            "current_company": "現在の会社",
            "current_position": "エンジニア",
            "experience_years": 5,
            "skills": ["Python", "JavaScript"],
            "education": "○○大学",
            "bizreach_url": "https://bizreach.jp/...",
            "raw_html": "<html>...</html>"
        }
    ],
    "session_id": "session-uuid",
    "client_id": "client-uuid"
}
```

**レスポンス:**
```json
{
    "status": "success",
    "received": 10,
    "processed": 10,
    "errors": []
}
```

### スクレイピングセッション管理

#### POST /api/scraping/session/start
スクレイピングセッションの開始

**リクエスト:**
```json
{
    "client_id": "client-uuid",
    "expected_count": 50,
    "search_criteria": {
        "keywords": ["Python", "エンジニア"],
        "location": "東京"
    }
}
```

**レスポンス:**
```json
{
    "session_id": "session-uuid",
    "status": "active",
    "started_at": "2024-01-01T00:00:00Z",
    "client_id": "client-uuid",
    "user_id": "user-uuid"
}
```

#### POST /api/scraping/session/{session_id}/complete
セッションの完了通知

**リクエスト:**
```json
{
    "total_processed": 50,
    "success_count": 48,
    "error_count": 2,
    "errors": [
        {
            "url": "https://bizreach.jp/...",
            "error": "タイムアウト"
        }
    ]
}
```

**レスポンス:**
```json
{
    "session_id": "session-uuid",
    "status": "completed",
    "completed_at": "2024-01-01T01:00:00Z",
    "summary": {
        "total_processed": 50,
        "success_count": 48,
        "error_count": 2
    }
}
```

### 採用要件管理

#### GET /api/requirements
採用要件一覧の取得

**クエリパラメータ:**
- `client_id`: クライアントIDでフィルタ
- `active_only`: `true` でアクティブな要件のみ取得
- `page`: ページ番号
- `per_page`: 1ページあたりの件数

**レスポンス:**
```json
{
    "requirements": [
        {
            "id": "uuid",
            "client_id": "client-uuid",
            "title": "バックエンドエンジニア募集",
            "description": "...",
            "is_active": true,
            "created_at": "2024-01-01T00:00:00Z"
        }
    ],
    "total": 25,
    "page": 1,
    "per_page": 20
}
```

#### POST /api/requirements
採用要件の作成

**リクエスト:**
```json
{
    "client_id": "client-uuid",
    "title": "バックエンドエンジニア募集",
    "description": "Python経験3年以上...",
    "original_text": "クライアントから受け取った原文"
}
```

**レスポンス:**
```json
{
    "id": "uuid",
    "client_id": "client-uuid",
    "title": "バックエンドエンジニア募集",
    "structured_data": {
        "position": "バックエンドエンジニア",
        "required_skills": ["Python", "Django"],
        "experience_years": 3,
        "...": "..."
    },
    "created_at": "2024-01-01T00:00:00Z"
}
```

### ジョブ管理

#### POST /api/jobs/matching
AIマッチングジョブの作成

**リクエスト:**
```json
{
    "requirement_id": "requirement-uuid",
    "candidate_source": {
        "type": "scraping_session",
        "session_id": "session-uuid"
    },
    "options": {
        "min_score": 70,
        "max_results": 100
    }
}
```

**レスポンス:**
```json
{
    "job_id": "job-uuid",
    "status": "pending",
    "created_at": "2024-01-01T00:00:00Z",
    "estimated_duration": 300
}
```

#### GET /api/jobs/{job_id}
ジョブステータスの取得

**レスポンス:**
```json
{
    "job_id": "job-uuid",
    "status": "in_progress",
    "progress": {
        "total": 100,
        "processed": 45,
        "percentage": 45
    },
    "started_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:05:00Z"
}
```

### 結果取得

#### GET /api/results/{job_id}
マッチング結果の取得

**クエリパラメータ:**
- `min_score`: 最小スコアでフィルタ
- `limit`: 結果数の上限
- `offset`: オフセット

**レスポンス:**
```json
{
    "job_id": "job-uuid",
    "results": [
        {
            "candidate_id": "candidate-uuid",
            "candidate_name": "候補者A",
            "match_score": 85.5,
            "match_reasons": [
                "Python経験が要件を満たしている",
                "類似業界での経験あり"
            ],
            "details": {
                "skill_match": 90,
                "experience_match": 80,
                "education_match": 85
            }
        }
    ],
    "total_results": 48,
    "sheets_url": "https://docs.google.com/spreadsheets/..."
}
```

## エラーレスポンス

すべてのエラーレスポンスは以下の形式で返されます：

```json
{
    "detail": "エラーメッセージ",
    "error_code": "ERROR_CODE",
    "timestamp": "2024-01-01T00:00:00Z"
}
```

### エラーコード一覧

| コード | HTTPステータス | 説明 |
|--------|---------------|------|
| UNAUTHORIZED | 401 | 認証エラー |
| FORBIDDEN | 403 | 権限エラー |
| NOT_FOUND | 404 | リソースが見つからない |
| VALIDATION_ERROR | 422 | バリデーションエラー |
| RATE_LIMIT | 429 | レート制限 |
| INTERNAL_ERROR | 500 | サーバー内部エラー |

## レート制限

- 認証済みユーザー: 1000リクエスト/時間
- 候補者バッチ送信: 100リクエスト/時間
- 大量データ取得: 10リクエスト/分

レート制限に達した場合、以下のヘッダーが返されます：
```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1704070800
```

## WebSocket API

### リアルタイム進捗通知

```javascript
// WebSocket接続
const ws = new WebSocket('wss://your-api.run.app/ws/{job_id}');

// メッセージ受信
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Progress:', data.progress);
};
```

**メッセージ形式:**
```json
{
    "type": "progress",
    "job_id": "job-uuid",
    "progress": {
        "total": 100,
        "processed": 45,
        "percentage": 45
    },
    "timestamp": "2024-01-01T00:00:00Z"
}
```

## SDKサンプル

### Python
```python
import requests

class RPOAPIClient:
    def __init__(self, base_url, token):
        self.base_url = base_url
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
    
    def get_clients(self, active_only=True):
        response = requests.get(
            f'{self.base_url}/api/clients',
            headers=self.headers,
            params={'active_only': active_only}
        )
        return response.json()
```

### JavaScript
```javascript
class RPOAPIClient {
    constructor(baseUrl, token) {
        this.baseUrl = baseUrl;
        this.headers = {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        };
    }
    
    async getClients(activeOnly = true) {
        const response = await fetch(
            `${this.baseUrl}/api/clients?active_only=${activeOnly}`,
            { headers: this.headers }
        );
        return await response.json();
    }
}
```