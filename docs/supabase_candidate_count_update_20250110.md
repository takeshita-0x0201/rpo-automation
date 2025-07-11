# Supabase候補者数取得の更新

## 実施日: 2025-07-10

## 更新内容

### 1. CandidateCounter サービスの更新

#### 変更ファイル: `/src/services/candidate_counter.py`

**主な変更点:**
1. 新しいcandidatesテーブル構造に対応
   - JSONB(`scraped_data->>`)からの取得を直接カラムアクセスに変更
   - `client_id`, `requirement_id`が独立したカラムとして存在

2. メソッドシグネチャの更新
   ```python
   # 旧: count_candidates(job_parameters, client_id)
   # 新: count_candidates(job_parameters, client_id, requirement_id)
   ```

3. 新規メソッドの追加
   - `count_by_requirement(requirement_id)`: 特定の採用要件IDに対する候補者数をカウント
   - `count_by_client(client_id)`: 特定のクライアントIDに対する候補者数をカウント

4. Supabaseクライアントの初期化
   - `SUPABASE_SERVICE_KEY`または`SUPABASE_KEY`を使用

### 2. WebApp (main.py) の更新

#### 変更ファイル: `/src/web/main.py`

**主な変更点:**
1. admin_jobs関数内でのcount_candidatesメソッド呼び出しを更新
   ```python
   # 変更前
   actual_count = candidate_counter.count_candidates(job_params, client_id)
   
   # 変更後
   requirement_id = job.get('requirement_id')
   actual_count = candidate_counter.count_candidates(job_params, client_id, requirement_id)
   ```

2. コメントの更新
   - "BigQueryから" → "Supabaseから"
   - "BigQuery接続エラー" → "Supabase接続エラー"

### 3. 影響範囲

以下の機能が正しく動作するようになりました：
- 管理者のジョブ管理画面での対象者数表示
- マネージャーのジョブ管理画面での対象者数表示
- ジョブ作成時の候補者数推定

### 4. データベース要件

以下のテーブル構造が必要です：

```sql
-- candidatesテーブル
CREATE TABLE candidates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id VARCHAR NOT NULL,
    candidate_link VARCHAR NOT NULL,
    candidate_company VARCHAR,
    candidate_resume TEXT,
    platform VARCHAR NOT NULL,
    client_id UUID NOT NULL REFERENCES clients(id),
    requirement_id UUID NOT NULL REFERENCES job_requirements(id),
    scraping_session_id UUID,
    scraped_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### 5. 環境変数

以下の環境変数が必要です：
- `SUPABASE_URL`: SupabaseプロジェクトのURL
- `SUPABASE_SERVICE_KEY`または`SUPABASE_KEY`: Supabaseのアクセスキー

### 6. テスト方法

1. WebAppを起動
   ```bash
   cd src/web
   python main.py
   ```

2. 管理者としてログイン

3. ジョブ管理画面（/admin/jobs）にアクセス

4. 各ジョブの「対象数」カラムに候補者数が表示されることを確認

### 7. 注意事項

1. **パフォーマンス**
   - 各ジョブごとに候補者数をカウントするため、ジョブが多い場合は表示に時間がかかる可能性があります
   - 必要に応じてキャッシュ機構の導入を検討してください

2. **エラーハンドリング**
   - Supabase接続エラー時は「取得エラー」と表示されます
   - 詳細なエラーはコンソールログに出力されます

3. **データ整合性**
   - candidatesテーブルにデータが存在しない場合は0件として表示されます
   - scraped_atの日付でフィルタリングされるため、古いデータは対象外となります