# BigQuery データベース構造ドキュメント

## プロジェクト: rpo-automation

### データセット構成

#### 1. client_learning
クライアント固有の学習・最適化データ

- **ai_accuracy_tracking**: AI判定精度の追跡
- **client_patterns**: クライアント固有のパターン
- **feedback_history**: フィードバック履歴
- **important_keywords**: 重要キーワード管理
- **prompt_templates**: プロンプトテンプレート
- **successful_hires**: 成功した採用記録

#### 2. recruitment_data
採用プロセスの中核データ

- **ai_evaluations**: AI評価結果
- **candidates**: 候補者情報
- **requirement_documents**: 採用要件ドキュメント
- **requirements**: 採用要件マスター
- **searches**: 検索ジョブ管理

#### 3. system_logs
システムログとモニタリング

- **api_access_logs**: APIアクセスログ
- **audit_logs**: 監査ログ
- **error_logs**: エラーログ
- **performance_metrics**: パフォーマンス指標
- **pubsub_logs**: Pub/Subメッセージログ
- **scraping_logs**: スクレイピングログ
- **daily_system_stats**: 日次統計（VIEW）
- **recent_critical_errors**: 最近のエラー（VIEW）

### データフロー

```
Chrome拡張機能 → candidates テーブル
                ↓
            ai_evaluations
                ↓
            client_patterns (学習)
```

### パーティショニング戦略

全テーブルで日次パーティション（60日保持）を採用：
- ストレージコストの最適化
- クエリパフォーマンスの向上
- 自動データライフサイクル管理

### クラスタリング

主要な検索キーでクラスタリング：
- client_id: クライアント別の分析
- search_id/requirement_id: ジョブ別の追跡
- status: ステータス別のフィルタリング

### 注意事項

1. 外部キー制約はBigQueryでサポートされていない
2. データ整合性はアプリケーション層で管理
3. JSON型を活用した柔軟なスキーマ設計