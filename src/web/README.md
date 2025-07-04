# RPO Automation WebApp

FastAPIベースのWebアプリケーション。採用要件管理、実行管理、結果確認の機能を提供します。

## 起動方法

### 方法1: 起動スクリプトを使用（推奨）
```bash
# プロジェクトルートから
./run_webapp.sh
```

### 方法2: 手動起動
```bash
# 仮想環境をアクティベート
source venv/bin/activate

# プロジェクトルートから起動
python -m uvicorn src.web.main:app --reload --port 8000
```

## アクセスURL

- **メインページ**: http://localhost:8000
- **API仕様書 (Swagger UI)**: http://localhost:8000/docs
- **API仕様書 (ReDoc)**: http://localhost:8000/redoc

## 主要なAPI エンドポイント

### 採用要件管理
- `GET /api/requirements/` - 採用要件一覧取得
- `POST /api/requirements/` - 新規採用要件作成
- `GET /api/requirements/{id}` - 特定の採用要件取得
- `PUT /api/requirements/{id}` - 採用要件更新
- `DELETE /api/requirements/{id}` - 採用要件削除

### ジョブ実行管理
- `GET /api/jobs/` - ジョブ一覧取得
- `POST /api/jobs/` - 新規ジョブ作成
- `GET /api/jobs/{id}` - ジョブ詳細取得
- `PUT /api/jobs/{id}/status` - ジョブステータス更新
- `POST /api/jobs/{id}/cancel` - ジョブキャンセル

### 結果確認
- `GET /api/results/searches` - 検索結果一覧
- `GET /api/results/searches/{id}` - 特定の検索結果
- `GET /api/results/searches/{id}/candidates` - 候補者一覧
- `GET /api/results/reports/client/{id}` - クライアント別レポート
- `POST /api/results/export/{id}` - Google Sheetsエクスポート

## 開発状況

現在、以下の機能が実装済みです：
- ✅ FastAPI基盤構築
- ✅ 基本的なAPIエンドポイント（モックデータ返却）
- ✅ CORS設定
- ✅ エラーハンドリング

次のステップ：
- [ ] Supabase連携（データ永続化）
- [ ] 認証機能実装
- [ ] フロントエンドUI実装
- [ ] Cloud Functions連携

## トラブルシューティング

### ポート使用中エラー
```bash
# ポート8000を使用中のプロセスを終了
lsof -ti:8000 | xargs kill -9
```

### モジュールインポートエラー
プロジェクトルートから起動していることを確認してください。

### 起動テスト
```bash
python test_webapp.py
```