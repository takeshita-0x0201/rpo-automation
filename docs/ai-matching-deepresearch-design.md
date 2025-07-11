# AIマッチング機能 - DeepResearchアプローチ設計メモ

## 概要
Microsoft DeepResearchのアルゴリズムを参考に、RPO AutomationのAIマッチング機能を反復的な深掘り評価方式で実装する設計案。

## DeepResearchアルゴリズムの特徴
- **反復的な調査**: 最大3回まで情報を深掘り
- **知識ギャップの特定**: 不足情報を見つけて追加分析
- **段階的な深化**: 表層的な評価から深い洞察へ

## RPO Automationへの適用案

### データソース
- BigQueryに保存された候補者データのみを使用
- 外部APIやWeb検索は使用しない

### 3段階評価フレームワーク

#### Phase 1: 表層マッチング（基本的な適合性チェック）
```
目的: 明示的な要件との照合
深さ: 表面的な情報のみ
内容:
- 必須スキルの有無（キーワードマッチ）
- 経験年数の数値的な合致
- 現在の役職レベル
- 業界経験の有無
```

#### Phase 2: 経験の質的評価（深い理解）
```
目的: 実務経験の深さと関連性の評価
深さ: 経験の文脈を理解
内容:
- スキルの実務での使用文脈
- プロジェクトの規模と複雑さ
- 担当した役割の詳細
- 技術選定の経験
```

#### Phase 3: 潜在能力評価（将来性）
```
目的: 成長性とポテンシャルの評価
深さ: キャリアパターンから推測
内容:
- キャリアの成長軌跡
- 学習能力（新技術習得の速さ）
- リーダーシップポテンシャル
- 組織適応力
```

## 反復の判断基準（案）

### Phase 1 → Phase 2への移行条件
1. スコアが中間的（60-80点）
2. 必須スキルは満たすが、詳細が不明
3. 経験年数は合致するが、具体的な実績が不明
4. 評価に「不明」「推測」が含まれる

### Phase 2 → Phase 3への移行条件
1. 基本要件は満たすが、差別化要因が不明確
2. 複数の候補者で差がつかない
3. 長期的な貢献可能性の評価が必要

### 早期終了条件
- Phase 1で90点以上 → 高適合で終了
- Phase 1で40点以下 → 不適合で終了

## 実装の基本構造

```python
class DeepResearchMatcher:
    def __init__(self):
        self.max_iterations = 3
        self.gemini_client = GeminiClient()
        
    async def match_candidate(self, requirement, candidate_data):
        results = []
        
        # Phase 1: 表層マッチング
        phase1_result = await self._phase1_evaluation(requirement, candidate_data)
        results.append(phase1_result)
        
        # 判断：Phase 2に進むか？
        if self._should_continue(phase1_result, phase=1):
            # Phase 2: 経験の質的評価
            phase2_result = await self._phase2_evaluation(
                requirement, 
                candidate_data, 
                previous_findings=phase1_result
            )
            results.append(phase2_result)
            
            # 判断：Phase 3に進むか？
            if self._should_continue(phase2_result, phase=2):
                # Phase 3: 潜在能力評価
                phase3_result = await self._phase3_evaluation(
                    requirement,
                    candidate_data,
                    previous_findings=results
                )
                results.append(phase3_result)
        
        # 最終評価をまとめる
        return self._synthesize_results(results)
```

## 未決定事項（要相談）

### 1. スコアリングの重み付け
- 案1: Phase 1: 40%、Phase 2: 40%、Phase 3: 20%
- 案2: 後のフェーズほど重要視
- 案3: 動的な重み付け（候補者タイプによって変更）

### 2. コスト最適化戦略
- 全候補者に3フェーズ実行？
- トップ20%の候補者のみPhase 3まで？
- 要件の重要度によって深さを調整？

### 3. 評価プロンプトの詳細設計
- 各フェーズでAIに与える具体的な指示
- 出力フォーマットの統一
- 評価の一貫性確保方法

### 4. パフォーマンス要件
- 1候補者あたりの処理時間目標
- 並列処理の実装方法
- API利用コストの上限

## 次のステップ
1. 上記の未決定事項を決定
2. Phase 1の評価プロンプト作成
3. プロトタイプ実装
4. テストデータでの検証
5. 本実装

## 参考
- [Microsoft DeepResearch](https://zenn.dev/microsoft/articles/ms-oss-deepresearch)
- 既存のAI評価実装: `/cloud_functions/search_candidates/ai_evaluator.py`