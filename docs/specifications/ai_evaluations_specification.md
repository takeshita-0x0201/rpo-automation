# ai_evaluationsテーブルとAIマッチングシステム仕様整理

## 現状の問題

1. **テーブル構造の不整合**: ai_evaluationsテーブルの実際の構造とAIマッチングサービスが期待する構造が一致していない
2. **データマッピングの不備**: AIマッチング結果とデータベースカラムのマッピングが不完全
3. **制約違反**: NOT NULL制約のあるカラムにnull値を挿入しようとしてエラーが発生

## AIマッチングシステムの出力構造

### 実際のAIマッチング結果
```python
{
    'final_score': 75,                    # int: 0-100のスコア
    'final_confidence': 'Medium',         # str: 'High', 'Medium', 'Low'
    'final_judgment': {
        'recommendation': 'B',            # str: 'A', 'B', 'C', 'D'
        'strengths': [                    # list[str]: 強み
            '豊富な実務経験',
            '必要な技術スキルを保有'
        ],
        'concerns': [                     # list[str]: 懸念事項
            '業界経験が不足',
            '転職回数がやや多い'
        ],
        'interview_points': [             # list[str]: 面接確認ポイント
            'チームビルディングの具体的な経験'
        ],
        'overall_assessment': 'string'    # str: 総合評価コメント
    },
    'total_cycles': 1,                    # int: 実行サイクル数
    'total_searches': 0                   # int: Web検索実行数
}
```

## 必要なai_evaluationsテーブル構造

### 必須カラム
```sql
CREATE TABLE ai_evaluations (
    -- 基本情報
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id UUID NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    requirement_id UUID NOT NULL REFERENCES job_requirements(id) ON DELETE CASCADE,
    search_id TEXT NOT NULL,  -- ジョブID（jobs.id）
    
    -- 評価結果
    ai_score FLOAT CHECK (ai_score >= 0 AND ai_score <= 100),  -- final_score
    match_score FLOAT CHECK (match_score >= 0 AND match_score <= 100),  -- final_scoreのコピー
    recommendation TEXT CHECK (recommendation IN ('A', 'B', 'C', 'D')),  -- final_judgment.recommendation
    confidence TEXT CHECK (confidence IN ('High', 'Medium', 'Low')),  -- final_confidence
    
    -- 詳細評価（配列形式）
    match_reasons TEXT[],     -- final_judgment.strengths
    concerns TEXT[],          -- final_judgment.concerns
    interview_points TEXT[],  -- final_judgment.interview_points
    overall_assessment TEXT,  -- final_judgment.overall_assessment
    
    -- メタデータ
    total_cycles INTEGER DEFAULT 0,      -- total_cycles
    total_searches INTEGER DEFAULT 0,    -- total_searches
    model_version TEXT,
    prompt_version TEXT,
    
    -- 詳細評価（JSON形式）- 後方互換性のため
    evaluation_result JSONB,  -- 全体の結果をJSONで保存
    
    -- タイムスタンプ
    evaluated_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

## データマッピング仕様

### AIマッチング結果 → データベース
```python
evaluation_data = {
    'id': str(uuid.uuid4()),
    'candidate_id': candidate['id'],                                    # 必須
    'requirement_id': candidate.get('requirement_id'),                 # 必須
    'search_id': job_id,                                               # 必須
    
    # スコア関連
    'ai_score': result.get('final_score', 0),                         # 0-100
    'match_score': result.get('final_score', 0),                      # ai_scoreと同じ値
    'recommendation': result.get('final_judgment', {}).get('recommendation', 'D'),  # A/B/C/D
    'confidence': result.get('final_confidence', 'Low'),              # High/Medium/Low
    
    # 詳細評価
    'match_reasons': result.get('final_judgment', {}).get('strengths', []),
    'concerns': result.get('final_judgment', {}).get('concerns', []),
    'interview_points': result.get('final_judgment', {}).get('interview_points', []),
    'overall_assessment': result.get('final_judgment', {}).get('overall_assessment', ''),
    
    # メタデータ
    'total_cycles': result.get('total_cycles', 0),
    'total_searches': result.get('total_searches', 0),
    'model_version': 'gemini-1.5-pro',  # 固定値
    'prompt_version': '1.0',            # 固定値
    
    # JSON形式での保存（後方互換性）
    'evaluation_result': {
        'strengths': result.get('final_judgment', {}).get('strengths', []),
        'concerns': result.get('final_judgment', {}).get('concerns', []),
        'interview_points': result.get('final_judgment', {}).get('interview_points', []),
        'overall_assessment': result.get('final_judgment', {}).get('overall_assessment', ''),
        'total_cycles': result.get('total_cycles', 0),
        'total_searches': result.get('total_searches', 0),
        'confidence': result.get('final_confidence', 'Low'),
        'recommendation': result.get('final_judgment', {}).get('recommendation', 'D')
    },
    
    'evaluated_at': datetime.utcnow().isoformat()
}
```

## 修正が必要な箇所

### 1. テーブル構造の統一
- 現在のai_evaluationsテーブルを上記仕様に合わせて修正
- 不要なカラムの削除、必要なカラムの追加

### 2. AIマッチングサービスの修正
- `_save_evaluation_result`メソッドを上記マッピング仕様に合わせて修正
- エラーハンドリングの改善

### 3. 制約の調整
- NOT NULL制約の適切な設定
- CHECK制約の追加（recommendation, confidenceの値制限）

## 実装優先順位

1. **高優先度**: テーブル構造の修正とデータマッピングの統一
2. **中優先度**: エラーハンドリングとログの改善
3. **低優先度**: パフォーマンス最適化とインデックス調整