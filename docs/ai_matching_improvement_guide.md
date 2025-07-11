# AIマッチング精度向上ガイド

## 目次
1. [概要](#概要)
2. [3つのアプローチの比較](#3つのアプローチの比較)
3. [推奨アプローチ：RAGを中心とした段階的実装](#推奨アプローチragを中心とした段階的実装)
4. [採用要件の重要性](#採用要件の重要性)
5. [実装ロードマップ](#実装ロードマップ)
6. [まとめ](#まとめ)

## 概要

AIマッチングの精度向上には、以下の3つのアプローチがあります：
- **ファインチューニング**: モデル自体を採用データで追加学習
- **RAG (Retrieval-Augmented Generation)**: 過去の採用事例を検索して参照
- **プロンプトエンジニアリング**: LLMへの指示を最適化

本ガイドでは、既存のピックアップデータ（評価理由、採用要件、合否結果など）を最大限活用するための戦略を解説します。

## 3つのアプローチの比較

### 1. ファインチューニング

#### 概要
採用マッチングに特化したデータセットでLLMを追加学習させる手法。

#### 強み
- 推論速度が速い（コンテキスト不要）
- 一貫性のある判断
- 長期的にはコスト効率が良い

#### 弱み
- 初期コスト高（$500-5000）
- 更新に再学習が必要
- 最低3000-5000件の高品質データが必要
- 判断理由の説明が困難

#### 必要なデータ例
```json
{
  "messages": [
    {
      "role": "system",
      "content": "あなたは採用マッチングの専門家です"
    },
    {
      "role": "user",
      "content": "候補者: 債権回収5年、マネジメント経験なし\n要件: 債権回収マネージャー"
    },
    {
      "role": "assistant",
      "content": "スコア: 80/100\n推奨度: 推奨\n理由: 実務経験豊富、マネジメントは成長可能性あり"
    }
  ]
}
```

### 2. RAG (Retrieval-Augmented Generation) ⭐推奨

#### 概要
過去の採用データをベクトル化して検索可能にし、類似ケースを参照しながら判断。

#### 強み
- **即座に更新可能**（新データをリアルタイム反映）
- **説明可能性が高い**（参照した事例を提示）
- **低コスト**（追加学習不要）
- **柔軟性**（クライアント別・職種別の調整が容易）

#### 弱み
- 検索処理による遅延
- ベクトルDBの運用が必要
- 検索精度に依存

#### 実装例
```python
def rag_matching(candidate, requirement):
    # 類似の成功事例を検索
    similar_cases = vector_db.search(
        query=f"{requirement.skills} {candidate.experience}",
        filter={"client_id": requirement.client_id, "result": "hired"},
        top_k=5
    )
    
    # コンテキストとして使用
    context = format_success_patterns(similar_cases)
    
    return llm.analyze(
        candidate=candidate,
        requirement=requirement,
        context=context
    )
```

### 3. プロンプトエンジニアリング

#### 概要
LLMへの指示（プロンプト）を最適化して精度向上。

#### 強み
- 実装が簡単
- コストが最も低い
- 即座に適用可能

#### 弱み
- 効果が限定的
- 過去データを活用できない
- 複雑な要件に対応困難

## 推奨アプローチ：RAGを中心とした段階的実装

### なぜRAGが最適か

1. **既存データの即活用**
   - ピックアップ履歴
   - 評価理由（Good/NG）
   - クライアントフィードバック
   - 採用結果

2. **継続的改善が容易**
   - 新しい評価結果を即座に反映
   - A/Bテストが簡単
   - 説明責任を果たせる

3. **期待される効果**
   ```
   月1: 精度60% → 70%（過去データ活用）
   月3: 精度70% → 80%（フィードバック蓄積）
   月6: 精度80% → 85%（パターン学習）
   ```

## 採用要件の重要性

### 学習データにおける採用要件の紐付けは必須

#### なぜ必須なのか

同じ候補者でも要件によって評価が変わる：

```python
candidate = "政策金融公庫で債権管理統括経験"

# ケース1: 実務担当者募集
requirement_1 = "債権回収実務担当者（現場経験必須）"
result_1 = "NG"  # 現場経験なし

# ケース2: 管理部門募集  
requirement_2 = "債権管理部門マネージャー"
result_2 = "Good"  # 統括経験あり

# ケース3: システム企画募集
requirement_3 = "債権管理システム企画担当"
result_3 = "Excellent"  # 直接活かせる経験
```

#### 適切な学習データ構造

```python
training_data = {
    # 採用要件（必須）
    "requirement": {
        "client": "債権回収会社A",
        "position": "債権回収マネージャー",
        "level": "課長級",
        "must_have": ["債権回収実務3年以上", "チーム管理経験"],
        "team_size": 10
    },
    
    # 候補者情報
    "candidate": {
        "current": "債権回収担当（係長）",
        "experience": "初期回収プロセス構築、5名管理"
    },
    
    # 評価結果
    "evaluation": {
        "result": "Good評価",
        "reason": "Manager経験なしだが実務理解深く成長可能"
    },
    
    # 採用後の追跡
    "outcome": {
        "hired": true,
        "performance_6m": "期待以上"
    }
}
```

#### 要件なしの問題点

- **精度低下**: 30-40%の精度低下
- **誤学習**: 文脈を無視した一般化
- **説明困難**: なぜその評価かが不明

## 実装ロードマップ

### Phase 1: Quick Win（1-2ヶ月）

1. **Week 1-2: データ準備**
   - pickup_historyのクレンジング
   - 採用要件との紐付け確認
   - 評価理由の正規化

2. **Week 3-4: 基本RAG構築**
   - Supabase pgvectorセットアップ
   - 埋め込み生成（OpenAI Embeddings）
   - 基本的な類似検索実装

### Phase 2: 高度化（3-4ヶ月）

1. **検索精度向上**
   ```python
   # マルチベクトル検索
   def multi_vector_search():
       skill_vector = embed(candidate.skills)
       experience_vector = embed(candidate.experience)
       
       results = weighted_search([
           (skill_vector, 0.4),
           (experience_vector, 0.6)
       ])
   ```

2. **フィードバックループ**
   ```python
   def update_with_outcome(evaluation_id, actual_result):
       # 新しい結果を即座にRAGに追加
       new_vector = embed(evaluation_case)
       vector_db.add(new_vector, metadata={
           'verified': True,
           'outcome': actual_result
       })
   ```

### Phase 3: 最適化（5-6ヶ月）

1. **セグメント別最適化**
   - クライアント別の重み調整
   - 職種別の検索戦略
   - レベル別の評価基準

2. **ハイブリッドアプローチ検討**
   - データが10,000件超えたらファインチューニング検討
   - RAGで対応困難な部分のみ補完

## 実装の具体例

### 1. データインデックス構築

```python
class RecruitmentRAGSystem:
    def index_evaluation_case(self, case):
        # 検索用テキスト作成
        case_text = f"""
        【採用要件】
        企業: {case['company']}
        職種: {case['position']}
        必須: {case['requirements']}
        
        【候補者】
        経歴: {case['candidate_summary']}
        
        【評価】
        結果: {case['result']}
        理由: {case['reason']}
        """
        
        # ベクトル化して保存
        embedding = self.embedder.embed_query(case_text)
        
        self.supabase.table('recruitment_vectors').insert({
            'content': case_text,
            'embedding': embedding,
            'metadata': {
                'client_id': case['client_id'],
                'result': case['result']
            }
        }).execute()
```

### 2. マッチング実行

```python
def evaluate_with_rag(candidate, requirement):
    # 1. 類似ケースを検索
    similar_cases = rag.search(
        query=format_query(candidate, requirement),
        filters={
            'client_id': requirement.client_id,
            'position_level': requirement.level
        },
        k=7
    )
    
    # 2. LLMで評価
    prompt = f"""
    過去の類似事例：
    {format_cases(similar_cases)}
    
    これらを参考に、以下を評価してください：
    候補者: {candidate}
    要件: {requirement}
    """
    
    return llm.evaluate(prompt)
```

## 成功のための重要ポイント

1. **データ品質の確保**
   - 評価理由の詳細記録
   - 採用要件の完全な紐付け
   - 結果の追跡（6ヶ月後評価など）

2. **継続的な改善**
   - 週次でのメトリクス確認
   - A/Bテストの実施
   - フィードバックの即時反映

3. **説明可能性の維持**
   - 参照した事例の記録
   - 判断根拠の可視化
   - クライアントへの説明資料

## まとめ

### 推奨アクション

1. **今すぐ開始**
   - pickup_historyと採用要件の紐付け確認
   - 簡易RAGシステムの構築（2週間）

2. **1ヶ月以内**
   - ベクトル検索の本格稼働
   - フィードバックループ構築

3. **継続的実施**
   - 評価結果の詳細記録
   - 定期的な精度測定
   - システムの段階的改善

### 期待される成果

- **短期（1-2ヶ月）**: 精度60% → 70%
- **中期（3-6ヶ月）**: 精度70% → 80-85%
- **長期（6ヶ月以降）**: 精度85%以上を維持

RAGを中心としたアプローチにより、既存データを最大限活用しながら、継続的に精度を向上させることが可能です。