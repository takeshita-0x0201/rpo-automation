# Google Apps Script - Supabase直接接続版

## 概要

GASから直接SupabaseのAPIを使用して、スプレッドシートのデータをclient_evaluationsテーブルに同期します。FastAPIサーバーを経由しないため、開発環境でも簡単に動作確認できます。

## セットアップ手順

### 1. GASファイルの準備

1. 既存の`Code.gs`はそのまま残す（候補者出力用）
2. 新規スクリプトファイルとして`ClientEvaluationUploaderDirect.gs`を追加
3. `ClientEvaluationUploader.gs`の内容をコピー

### 2. スクリプトプロパティの設定

GASエディタで以下を実行：

```javascript
setupSupabaseProperties();
```

これにより以下が設定されます：
- `SUPABASE_URL`: Supabaseプロジェクトのベース URL
- `SUPABASE_ANON_KEY`: 公開用APIキー
- `SUPABASE_SERVICE_KEY`: サービスロール用APIキー（RLS回避）

### 3. 定期実行トリガーの設定

```javascript
setupDirectSyncTrigger();
```

これで1時間ごとに`syncClientEvaluationsDirectly`が実行されます。

## 動作の流れ

```
スプレッドシート
    ↓ (GASが読み取り)
GAS (直接Supabase APIを呼び出し)
    ↓ (REST API)
Supabase (client_evaluations)
```

## テスト方法

### 手動実行
```javascript
// GASエディタで実行
syncClientEvaluationsDirectly();
```

### デバッグ用関数
```javascript
// 特定の候補者IDを検索
function testFindCandidate() {
  const id = findCandidateId("山田太郎");
  console.log("Found ID:", id);
}

// 特定の求人を検索
function testFindRequirement() {
  const id = findRequirementId("シニアエンジニア");
  console.log("Found ID:", id);
}
```

## メリット

1. **開発環境での動作**: localhostやngrokが不要
2. **シンプル**: FastAPIサーバーを経由しない
3. **直接的**: Supabaseとの通信が直接確認できる

## 注意事項

- `SUPABASE_SERVICE_KEY`は機密情報です。本番環境では適切に管理してください
- レート制限に注意（Supabaseの無料プランは500リクエスト/秒）
- エラーハンドリングは基本的なものです。必要に応じて拡張してください

## FastAPI連携への移行

本番環境でFastAPIサーバーを使用する場合：

1. 元の`ClientEvaluationUploader.gs`を使用
2. `API_ENDPOINT`を本番URLに変更
3. トリガーを`syncClientEvaluations`に変更

両方のスクリプトを共存させることで、開発と本番を使い分けることができます。