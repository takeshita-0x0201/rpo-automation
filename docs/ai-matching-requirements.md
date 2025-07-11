# AIマッチング機能の要件

## 概要
RPO AutomationのAIマッチング機能は、採用要件と候補者データを自動的に照合し、適合度をスコアリングする機能です。

## システム構成

### 使用するAI
- **Gemini API** (gemini-2.0-flash-exp): 採用要件の構造化
- **OpenAI API** (GPT-4-turbo-preview): 候補者評価（Cloud Function実装）

## 主要コンポーネント

### 1. データソース
```
Chrome拡張機能（BizReach）
    ↓ スクレイピング
BigQuery (candidates テーブル)
    ↓ 最新データ取得
AIマッチングエンジン
```

### 2. 処理フロー

#### Phase 1: 採用要件の構造化
```python
入力: フリーテキストの採用要件
   ↓ Gemini API
出力: 構造化されたJSON
{
    "title": "職種名",
    "position": "ポジション",
    "required_skills": ["必須スキル1", "必須スキル2"],
    "preferred_skills": ["歓迎スキル1", "歓迎スキル2"],
    "experience_years_min": 3,
    "experience_years_max": 10,
    "education_level": "学歴要件",
    "salary_min": 500,
    "salary_max": 800,
    "work_location": "東京",
    "employment_type": "正社員"
}
```

#### Phase 2: 候補者データの取得
```sql
-- BigQueryから最新の候補者データを取得
SELECT 
    candidate_id,
    name,
    current_company,
    current_position,
    experience,
    skills,
    education
FROM recruitment_data.candidates
WHERE scraped_at >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
```

#### Phase 3: AIによる評価
```python
評価項目:
1. ポジションマッチ度
2. 必須スキルの充足度
3. 歓迎スキルの保有状況
4. 経験年数の適合性
5. 企業文化とのフィット感

出力形式:
{
    "score": 85,  # 0-100点
    "summary": "エンジニアとしての経験が豊富で、必須スキルを満たしています",
    "recommendation": "highly_recommended",  # 推奨レベル
    "match_reasons": [
        "Python/Djangoの実務経験5年以上",
        "AWSでのインフラ構築経験あり"
    ],
    "concerns": [
        "マネジメント経験が要件より少ない"
    ],
    "detailed_evaluation": "詳細な評価文..."
}
```

### 3. 評価基準

#### スコアリング（100点満点）
- **90-100点**: 非常に高い適合度（highly_recommended）
- **70-89点**: 高い適合度（recommended）
- **50-69点**: 中程度の適合度（neutral）
- **0-49点**: 低い適合度（not_recommended）

#### 評価の重み付け
```python
weights = {
    "position_match": 0.25,      # 25%
    "required_skills": 0.35,     # 35%
    "preferred_skills": 0.15,    # 15%
    "experience_years": 0.15,    # 15%
    "culture_fit": 0.10         # 10%
}
```

### 4. 出力と保存

#### BigQueryへの保存
```sql
-- ai_evaluations テーブル
CREATE TABLE recruitment_data.ai_evaluations (
    id STRING,
    candidate_id STRING,
    requirement_id STRING,
    search_id STRING,
    ai_score FLOAT64,
    match_reasons ARRAY<STRING>,
    concerns ARRAY<STRING>,
    recommendation STRING,
    detailed_evaluation JSON,
    evaluated_at TIMESTAMP,
    model_version STRING,
    prompt_version STRING
)
PARTITION BY DATE(evaluated_at)
CLUSTER BY search_id, recommendation;
```

#### Google Sheetsへの出力
- 高スコア順にソート
- カラム: 候補者名、現職、スコア、推奨レベル、マッチ理由、懸念点

### 5. 実行パラメータ（Web UIから設定）

#### データソース選択
- **最新データ**: 直近30日以内の収集データ
- **期間指定**: 開始日〜終了日を指定

#### マッチング閾値
- **高（80%以上）**: 非常に適合度の高い候補者のみ
- **中（60%以上）**: 適合度の高い候補者
- **低（40%以上）**: ある程度適合する候補者
- **全て**: 閾値なし

#### 出力形式
- ✅ Google Sheetsに出力
- ✅ BigQueryに保存

## 実装状況

### 実装済み
- ✅ Web UIでのジョブ作成機能
- ✅ 採用要件の構造化（Gemini API）
- ✅ ジョブ管理（作成・実行・停止・削除）
- ✅ Chrome拡張機能（BizReachからのデータ収集）
- ✅ BigQueryへの候補者データ保存機能

### Chrome拡張機能の実装内容
- JWT認証によるセキュアなログイン
- BizReachからの候補者データ自動収集
- バッチ処理による効率的なデータ送信
- `/api/extension/candidates/batch`エンドポイント経由でデータ送信
- Supabase経由でBigQueryへ自動アップロード

### 未実装
- ❌ AIマッチングエンジン（実際の評価処理）
- ❌ 評価結果のBigQuery保存
- ❌ Google Sheetsへの出力
- ❌ ジョブ実行時のAIマッチング処理連携

## 今後の実装優先順位

1. **AIマッチングエンジンの実装**（最優先）
   - BigQueryからのデータ取得
   - OpenAI/Gemini APIを使った評価
   - スコアリングロジックの実装

3. **結果出力機能**
   - BigQueryへの評価結果保存
   - Google Sheetsへのエクスポート

4. **モニタリング・分析機能**
   - マッチング精度の分析
   - 評価履歴の可視化

## セキュリティ・コンプライアンス

- 候補者の個人情報は適切に保護
- APIキーは環境変数で管理
- アクセス権限はロールベースで制御
- データは暗号化して保存