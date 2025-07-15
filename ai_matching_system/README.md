# AI Matching System

AIを活用した採用候補者マッチングシステム

## ディレクトリ構成

```
ai_matching_system/
├── README.md                          # このファイル
├── requirements.txt                   # 必要なPythonパッケージ
├── API_KEY_SETUP.md                  # APIキー設定ガイド
├── AI_MATCHING_README.md             # AIマッチングシステムの詳細説明
├── SEPARATED_ARCHITECTURE_README.md   # 分離型アーキテクチャの説明
├── MEMO_ONLY_ARCHITECTURE.md         # 求人メモベース評価の説明
│
├── run_separated_matching.py          # メイン実行スクリプト（分離型）
├── run_matching_memo_only.py          # 求人メモのみ使用版
├── run_matching.py                    # 従来版実行スクリプト
├── test_matching_demo.py              # デモスクリプト（APIキー不要）
│
├── sample_data/                       # サンプルデータ
│   ├── resume.txt                     # 候補者レジュメ
│   ├── job_description.txt            # 求人票
│   └── job_memo.txt                   # 求人メモ
│
└── ai_matching/                       # メインモジュール
    ├── __init__.py
    ├── deep_research_matcher.py       # 従来版マッチャー
    ├── deep_research_modular.py       # モジュラー版
    ├── evaluation_patterns.py         # 評価パターン定義
    └── nodes/                         # 処理ノード
        ├── __init__.py
        ├── base.py                    # 基底クラス
        ├── orchestrator.py            # オーケストレーター
        ├── evaluator.py               # 評価ノード
        ├── gap_analyzer.py            # ギャップ分析ノード
        ├── searcher.py                # Web検索ノード
        ├── reporter.py                # レポート生成ノード
        ├── memo_processor.py          # 求人メモ処理
        └── requirement_checker.py     # 必須要件チェッカー
```

## セットアップ

### 1. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 2. APIキーの設定

```bash
export GEMINI_API_KEY='your-gemini-api-key'
export TAVILY_API_KEY='your-tavily-api-key'  # オプション
```

詳細は `API_KEY_SETUP.md` を参照してください。

## 使用方法

### 基本的な実行

```bash
# 分離型アーキテクチャ版（推奨）
python run_separated_matching.py

# デモ版（APIキー不要）
python test_matching_demo.py
```

### サンプルデータの編集

`sample_data/` ディレクトリ内のファイルを編集して、独自のデータでテストできます：

- `resume.txt`: 候補者の職務経歴
- `job_description.txt`: 求人票
- `job_memo.txt`: 求人メモ（必須要件など）

## 評価ロジック

### 推奨度の基準

- **A**: 全ての必須要件を満たし、かつ高評価（必須要件100%充足 + スコア70点以上）
- **B**: 一部の必須要件を満たす（必須要件を1つ以上満たすが、全ては満たさない）
- **C**: 必須要件は満たさないが、ポテンシャルはある
- **D**: 必須要件を満たさず、その他の評価も低い

### 処理フロー

1. **第1段階: 必須要件チェック**
   - 求人メモから必須要件を抽出
   - レジュメとの照合
   - 充足率の計算

2. **第2段階: 詳細評価**（最大3サイクル）
   - 候補者評価
   - 情報ギャップ分析
   - 追加情報収集（Web検索）

3. **最終レポート生成**
   - 総合評価
   - 面接確認事項

## トラブルシューティング

### APIキーエラー

```
エラー: GEMINI_API_KEY環境変数が設定されていません
```

→ `export GEMINI_API_KEY='your-api-key'` を実行

### インポートエラー

```
ModuleNotFoundError: No module named 'google.generativeai'
```

→ `pip install -r requirements.txt` を実行

## 詳細ドキュメント

- システム概要: `AI_MATCHING_README.md`
- アーキテクチャ詳細: `SEPARATED_ARCHITECTURE_README.md`
- 評価ロジック詳細: `MEMO_ONLY_ARCHITECTURE.md`