# Chrome拡張機能更新まとめ

## 実施日: 2025-07-10

## 変更内容

### 1. Candidatesテーブル構造の変更

#### 新しい必須カラム
- `candidate_id` - プラットフォーム上の候補者ID
- `candidate_link` - 候補者プロフィールURL
- `candidate_company` - 所属企業
- `candidate_resume` - レジュメ情報
- `platform` - プラットフォーム名（デフォルト: 'bizreach'）

#### リレーションカラム（正規化）
- `client_id` (UUID) - 外部キー
- `requirement_id` (UUID) - 外部キー
- `scraping_session_id` (UUID) - 外部キー

### 2. Chrome拡張機能の更新

#### `/src/extension/content/scrapers/bizreach.js`
- `extractCandidateData`メソッドを新しいテーブル構造に対応
- `extractCandidateId`メソッドを追加（URLからID抽出）
- `extractFromPattern`メソッドを追加（テキストパターンマッチング）

主な変更点：
```javascript
const data = {
  // 新しいテーブル構造
  candidate_id: candidateId || `bizreach_${Date.now()}_${index}`,
  candidate_link: candidateUrl,
  candidate_company: this.extractText(...),
  candidate_resume: candidateUrl,
  platform: 'bizreach',
  
  // リレーション
  client_id: this.sessionInfo.clientId,
  requirement_id: this.sessionInfo.requirementId,
  scraping_session_id: this.sessionInfo.sessionId,
  
  // 後方互換性のためのフィールドも維持
  ...
};
```

### 3. APIエンドポイントの更新

#### `/src/web/routers/extension_api.py`

1. **CandidateDataモデルの更新**
   - 新しい必須フィールドを追加
   - 旧フィールドをオプショナルに変更

2. **save_candidates_batchエンドポイントの更新**
   - 新しいテーブル構造にデータをマッピング
   - 後方互換性のための変換ロジック追加
   - scraped_byをUUID型に変更

### 4. データベース移行

#### 実行済みSQL
- `alter_candidates_table_final.sql` - テーブル構造の更新

## 移行期間中の対応

### 後方互換性の維持
1. Chrome拡張機能は新旧両方のフィールドを送信
2. APIは両方のフィールドを処理可能
3. 旧フィールドから新フィールドへの自動マッピング

### データ整合性
- `candidate_id`がない場合はURLから自動抽出
- `platform`のデフォルト値は'bizreach'
- ユニーク制約: `(candidate_id, platform)`

## テスト手順

1. **テーブル構造の確認**
```sql
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'candidates'
AND column_name IN ('candidate_id', 'candidate_link', 'candidate_company', 'candidate_resume');
```

2. **Chrome拡張機能のテスト**
- Bizreachで候補者一覧ページを開く
- スクレイピングを実行
- 開発者ツールでデータ構造を確認

3. **APIのテスト**
- `/api/extension/candidates/batch`エンドポイントへのPOSTを確認
- Supabaseでデータが正しく保存されているか確認

## 今後の作業

1. **旧カラムの削除**（移行完了後）
   - name, email, phone等の未使用カラム
   - bizreach_id, bizreach_url（新カラムに統合）
   - scraped_data（正規化完了後）

2. **パフォーマンス最適化**
   - インデックスの効果測定
   - クエリの最適化

3. **他プラットフォーム対応**
   - Green、Wantedly等のスクレイパー追加
   - プラットフォーム別のID形式対応