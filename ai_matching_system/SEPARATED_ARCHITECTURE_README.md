# 分離型DeepResearchアーキテクチャ

## 概要
分離型アーキテクチャでは、DeepResearchの各処理段階を独立したノードとして実装しています。
これにより、高い拡張性と保守性を実現しています。

## アーキテクチャ構成

### ノード構成
```
┌─────────────────┐     ┌──────────────┐     ┌─────────────┐
│ EvaluatorNode   │ --> │ GapAnalyzer  │ --> │ Searcher    │
│ (評価)          │     │ (ギャップ分析)│     │ (Web検索)   │
└─────────────────┘     └──────────────┘     └─────────────┘
         ↑                                            │
         └────────────────────────────────────────────┘
                        (サイクル)
                              ↓
                    ┌──────────────────┐
                    │ ReporterNode     │
                    │ (最終レポート)    │
                    └──────────────────┘
```

### 各ノードの役割

1. **EvaluatorNode** (`evaluator.py`)
   - 候補者の評価を行う
   - スコア（0-100）と確信度（低/中/高）を算出
   - 強みと懸念点を特定

2. **GapAnalyzerNode** (`gap_analyzer.py`)
   - 評価の不確実性を分析
   - 判断に必要な追加情報を特定
   - Web検索クエリを生成

3. **TavilySearcherNode** (`searcher.py`)
   - Tavily APIを使用してWeb検索を実行
   - 検索結果を要約
   - APIが利用できない場合はシミュレーション

4. **ReportGeneratorNode** (`reporter.py`)
   - 全サイクルの結果を統合
   - 最終的な推奨度（A/B/C/D）を決定
   - 面接確認事項を生成

5. **Orchestrator** (`orchestrator.py`)
   - 各ノードの実行を管理
   - 状態管理とサイクル制御
   - 結果の集約

## セットアップ

### 1. 必要なパッケージのインストール
```bash
pip install google-generativeai
pip install tavily-python  # Tavily Web検索を使用する場合
```

### 2. APIキーの設定
```bash
# Gemini API（必須）
export GEMINI_API_KEY='your-gemini-api-key'

# Tavily API（オプション - Web検索に使用）
export TAVILY_API_KEY='your-tavily-api-key'
```

## 使用方法

### 実行スクリプトを使用
```bash
python run_separated_matching.py
```

### プログラムから使用
```python
from src.ai_matching.nodes import SeparatedDeepResearchMatcher

# マッチャーの初期化
matcher = SeparatedDeepResearchMatcher(
    gemini_api_key='your-gemini-key',
    tavily_api_key='your-tavily-key'  # オプション
)

# マッチング実行
result = matcher.match_candidate(
    'path/to/resume.txt',
    'path/to/job_description.txt',
    'path/to/job_memo.txt',
    max_cycles=3
)

# 結果の取得
print(f"推奨度: {result['final_judgment']['recommendation']}")
```

### 非同期処理として使用
```python
import asyncio
from src.ai_matching.nodes import DeepResearchOrchestrator

async def run_matching():
    orchestrator = DeepResearchOrchestrator(
        gemini_api_key='your-key',
        tavily_api_key='your-tavily-key'
    )
    
    result = await orchestrator.run(
        resume="候補者の経歴...",
        job_description="求人内容...",
        job_memo="補足メモ...",
        max_cycles=3
    )
    
    return result

# 実行
result = asyncio.run(run_matching())
```

## データ構造

### ResearchState
全体の状態を管理するデータクラス：
```python
@dataclass
class ResearchState:
    resume: str                    # レジュメ
    job_description: str          # 求人票
    job_memo: str                 # 求人メモ
    current_evaluation: Optional[EvaluationResult]  # 現在の評価
    information_gaps: List[InformationGap]          # 情報ギャップ
    search_results: Dict[str, SearchResult]         # 検索結果
    evaluation_history: List[CycleResult]           # 評価履歴
    current_cycle: int            # 現在のサイクル
    max_cycles: int              # 最大サイクル数
    should_continue: bool        # 継続フラグ
    final_judgment: Optional[Dict]  # 最終判定
```

### 主要な出力形式
```python
{
    'final_judgment': {
        'recommendation': 'B',        # A/B/C/D
        'strengths': [...],          # 強み（3つ）
        'concerns': [...],           # 懸念点（2つ）
        'overall_assessment': '...',  # 総合評価
        'interview_points': [...]     # 面接確認事項（3つ）
    },
    'evaluation_history': [...],      # 各サイクルの履歴
    'total_cycles': 3,               # 実行サイクル数
    'total_searches': 2,             # Web検索実行回数
    'final_score': 75,               # 最終スコア
    'final_confidence': '高'         # 最終確信度
}
```

## 拡張方法

### 新しいノードの追加
1. `BaseNode`を継承したクラスを作成
2. `process`メソッドを実装
3. Orchestratorに組み込む

```python
from src.ai_matching.nodes.base import BaseNode, ResearchState

class CustomNode(BaseNode):
    def __init__(self, name: str):
        super().__init__(name)
    
    async def process(self, state: ResearchState) -> ResearchState:
        # カスタム処理を実装
        return state
```

### 検索エンジンの変更
`TavilySearcherNode`の`_search_information`メソッドを変更することで、
他の検索APIに切り替えることができます。

## トラブルシューティング

### Tavily APIが利用できない場合
環境変数`TAVILY_API_KEY`が設定されていない場合、自動的にシミュレーションモードで動作します。

### メモリ使用量が多い場合
`max_cycles`を減らすことで、処理サイクル数を制限できます。

### 処理時間が長い場合
各ノードは独立しているため、必要に応じて並列処理に変更することも可能です。

## パフォーマンス最適化

1. **キャッシュの活用**
   - 同じクエリの検索結果をキャッシュ
   - LLMの応答をキャッシュ

2. **並列処理**
   - 複数の候補者を並列で処理
   - 検索クエリを並列実行

3. **早期終了**
   - 確信度が「高」になった時点で終了
   - スコアが極端に低い場合は早期終了