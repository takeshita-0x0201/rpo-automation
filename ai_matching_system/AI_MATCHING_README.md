# DeepResearch AIマッチングシステム

## 概要
DeepResearchアルゴリズムを使用した採用候補者マッチングシステムです。
「評価→不足情報特定→検索」のサイクルを繰り返し、段階的に評価精度を高めていきます。

## 実装タイプ

本システムは2つの実装方式を提供しています：

### 1. 統合型実装（シンプル版）
- 単一クラスで全機能を実装
- シンプルで理解しやすい
- 小規模な利用に最適

### 2. 分離型実装（モジュラー版）
- 各処理を独立したノードとして実装
- 高い拡張性と保守性
- Tavily Web検索API対応
- 大規模・本番環境向け

## セットアップ

### 1. 必要なパッケージのインストール
```bash
# 基本パッケージ
pip install google-generativeai

# 分離型実装でTavily Web検索を使用する場合
pip install tavily-python
```

### 2. APIキーの設定

APIキーの設定方法は複数あります。詳細は[APIキー設定ガイド](API_KEY_SETUP.md)を参照してください。

#### 簡単な設定方法（環境変数）
```bash
# Gemini APIキー（必須）
export GEMINI_API_KEY='your-gemini-api-key-here'

# Tavily APIキー（オプション：分離型実装でWeb検索を使用する場合）
export TAVILY_API_KEY='your-tavily-api-key-here'
```

#### .envファイルを使用する場合
```bash
# .env.exampleをコピー
cp .env.example .env

# .envファイルを編集してAPIキーを設定
# GEMINI_API_KEY=your-actual-key
# TAVILY_API_KEY=your-actual-key
```

APIキーは以下から取得できます：
- Gemini: [Google AI Studio](https://makersuite.google.com/app/apikey)
- Tavily: [Tavily Dashboard](https://app.tavily.com/)

## 使用方法

### 統合型実装の実行
```bash
# シンプルな統合型実装
python run_matching.py
```

### 分離型実装の実行
```bash
# モジュラーな分離型実装（Tavily対応）
python run_separated_matching.py
```

### プログラムからの使用

#### 統合型実装
```python
from src.ai_matching.deep_research_matcher import DeepResearchMatcher

# マッチャー作成
matcher = DeepResearchMatcher(api_key='your-api-key')

# マッチング実行
result = matcher.match_candidate(
    'path/to/resume.txt',
    'path/to/job_description.txt',
    'path/to/job_memo.txt'
)
```

#### 分離型実装
```python
from src.ai_matching.nodes import SeparatedDeepResearchMatcher

# マッチャー作成（Tavily APIキーはオプション）
matcher = SeparatedDeepResearchMatcher(
    gemini_api_key='your-gemini-key',
    tavily_api_key='your-tavily-key'  # 省略可能
)

# マッチング実行
result = matcher.match_candidate(
    'path/to/resume.txt',
    'path/to/job_description.txt',
    'path/to/job_memo.txt',
    max_cycles=3
)
```

## 処理フロー

1. **サイクル1: 初期評価**
   - 基本的な要件適合性を評価
   - 明らかな強みと懸念点を特定
   - 不明確な点を洗い出し

2. **サイクル2: 深掘り評価**
   - 不足情報を検索・収集
   - より詳細な適合性評価
   - 特定領域の深い分析

3. **サイクル3: 最終評価**
   - 追加情報を統合
   - 最終的な推奨度決定
   - 面接での確認事項整理

## 評価基準

- **A評価 (80-100点)**: 非常に優秀で即戦力。強く推奨
- **B評価 (60-79点)**: 要件を満たし活躍が期待できる。推奨
- **C評価 (40-59点)**: 一部懸念はあるが検討の価値あり
- **D評価 (0-39点)**: 要件との乖離が大きい。推奨しない

## サンプルデータ

`sample_data/`ディレクトリに以下のサンプルファイルが含まれています：

- `resume.txt`: 候補者のレジュメ
- `job_description.txt`: 求人票
- `job_memo.txt`: 採用チームからの補足メモ

## 出力例

```
=== 最終マッチング結果 ===

【推奨度】 B

【強み】
  ✓ 財務・資金管理の実務経験が豊富（7年以上）
  ✓ ERPシステム（SAP）の深い使用経験
  ✓ マネジメント経験とプロセス改善実績

【懸念点】
  ⚠ 英語力が要件に達していない（TOEIC 650点）
  ⚠ グローバル企業での実務経験が限定的

【総合評価】
  財務の実務経験は申し分なく、システム移行への適応力も期待できる。
  ただし、英語力の向上が必須で、入社後のサポートが必要。

【面接確認事項】
  1. 英語での実務経験の具体例と改善意欲
  2. 新システム習得時の過去の経験
  3. グローバルチームとの協働への意欲
```

## 実装の選択基準

### 統合型実装を選ぶべき場合
- シンプルな実装を求めている
- 少数の候補者を処理する
- Web検索は不要（シミュレーションで十分）
- コードの理解しやすさを重視

### 分離型実装を選ぶべき場合
- 本番環境での利用を想定
- 大量の候補者を処理する必要がある
- 実際のWeb検索機能が必要
- 将来的な拡張・カスタマイズを予定
- 各処理の詳細なモニタリングが必要

## ファイル構成

```
src/ai_matching/
├── deep_research_matcher.py      # 統合型実装
├── deep_research_modular.py      # モジュラー版（参考実装）
└── nodes/                        # 分離型実装
    ├── __init__.py
    ├── base.py                   # 基底クラスとデータ構造
    ├── evaluator.py              # 評価ノード
    ├── gap_analyzer.py           # ギャップ分析ノード
    ├── searcher.py               # Tavily検索ノード
    ├── reporter.py               # レポート生成ノード
    └── orchestrator.py           # オーケストレーター
```

## 注意事項

- Gemini APIの利用制限に注意してください
- 大量の候補者を処理する場合は、適切な間隔を空けてください
- 統合型実装のWeb検索機能はシミュレーションです
- 分離型実装でTavily APIキーが設定されていない場合も、自動的にシミュレーションモードになります

## トラブルシューティング

### APIキーエラー
```bash
# Gemini APIキーの確認
export GEMINI_API_KEY='your-actual-api-key'

# Tavily APIキーの確認（分離型実装のみ）
export TAVILY_API_KEY='your-tavily-api-key'
```

### ファイルが見つからない
サンプルデータのパスを確認し、正しいディレクトリから実行してください。

### API制限エラー
- Gemini API: リクエスト間隔を調整するか、しばらく待ってから再実行
- Tavily API: 無料プランの制限を確認（月1000リクエストまで）

### Tavilyライブラリのインストールエラー
```bash
pip install --upgrade pip
pip install tavily-python
```

## 関連ドキュメント

- [分離型アーキテクチャの詳細](SEPARATED_ARCHITECTURE_README.md)
- [統合型実装のコード](src/ai_matching/deep_research_matcher.py)
- [分離型実装のコード](src/ai_matching/nodes/)