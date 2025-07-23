# AI Matching System

AIを活用した採用候補者マッチングシステム

## 概要

このシステムは、DeepResearchアルゴリズムとRAG（Retrieval-Augmented Generation）を組み合わせて、候補者と求人の高精度なマッチングを実現します。

## ディレクトリ構成

```
ai_matching_system/
├── README.md                    # このファイル
├── requirements.txt             # 依存パッケージ
├── run_separated_matching.py    # メイン実行スクリプト
│
├── ai_matching/                 # コアモジュール
│   ├── nodes/                   # 処理ノード
│   │   ├── evaluator.py        # 評価ノード
│   │   ├── gap_analyzer.py     # ギャップ分析
│   │   ├── searcher.py         # Web検索
│   │   ├── rag_searcher.py     # RAG検索
│   │   └── reporter.py         # レポート生成
│   ├── rag/                     # RAG関連
│   │   ├── vector_manager.py   # ベクトル管理
│   │   ├── vector_db.py        # ベクトルDB
│   │   └── feedback_loop.py    # フィードバック
│   └── embeddings/              # 埋め込み
│       └── gemini_embedder.py  # Gemini埋め込み
│
├── scripts/                     # ユーティリティスクリプト
│   ├── enrich_historical_data.py     # 過去データのエンリッチメント
│   ├── vectorize_historical_data.py  # ベクトル化
│   ├── search_similar_cases.py       # 類似ケース検索
│   ├── analyze_evaluation_diff.py    # 評価差分分析
│   └── README_*.md                   # 各種ドキュメント
│
├── sample_data/                 # サンプルデータ
│   ├── resume.txt              # 候補者レジュメ
│   ├── job_description.txt     # 求人票
│   └── job_memo.txt            # 求人メモ
│
├── data/                        # データ格納
│   └── evaluation_results/      # 評価結果
│
└── docs/                        # ドキュメント
    ├── AI_MATCHING_README.md   # 詳細説明
    ├── SEPARATED_ARCHITECTURE_README.md  # アーキテクチャ
    └── API_KEY_SETUP.md        # API設定ガイド
```

## クイックスタート

### 1. 環境設定

```bash
# 仮想環境の作成
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 依存パッケージのインストール
pip install -r requirements.txt
```

### 2. APIキーの設定

```bash
export GEMINI_API_KEY="your-gemini-api-key"
export TAVILY_API_KEY="your-tavily-api-key"  # オプション
export PINECONE_API_KEY="your-pinecone-key"   # オプション
```

### 3. 実行

```bash
# 基本的な評価実行
python run_separated_matching.py \
  sample_data/resume.txt \
  sample_data/job_description.txt \
  sample_data/job_memo.txt

# Web検索を無効化
python run_separated_matching.py \
  sample_data/resume.txt \
  sample_data/job_description.txt \
  sample_data/job_memo.txt \
  --no-web-search
```

## 主要機能

### 1. DeepResearch評価
- 複数サイクルでの段階的評価
- 情報ギャップの特定と補完
- 評価精度の継続的改善

### 2. RAG（類似ケース検索）
- 過去の評価事例を参照
- クライアント評価傾向の学習
- リスク要因の早期発見

### 3. プロンプト最適化
- 必須要件: 60%、実務経験: 25%、技術力: 15%の配点
- 曖昧表現の排除
- 保守的評価による過大評価防止

## ユーティリティスクリプト

### 過去データのエンリッチメント
```bash
python scripts/enrich_historical_data.py \
  evaluation_data.csv \
  "財務・経理" \
  sample_data/job_description.txt \
  sample_data/job_memo.txt
```

### ベクトルデータベースの構築
```bash
python scripts/vectorize_historical_data.py \
  data/evaluation_results/evaluation_results.json
```

### 類似ケース検索
```bash
python scripts/search_similar_cases.py \
  sample_data/resume.txt \
  sample_data/job_description.txt \
  sample_data/job_memo.txt
```

## 詳細ドキュメント

- [AIマッチングシステム詳細](docs/AI_MATCHING_README.md)
- [アーキテクチャ説明](docs/SEPARATED_ARCHITECTURE_README.md)
- [APIキー設定ガイド](docs/API_KEY_SETUP.md)
- [ベクトルDB実装ガイド](scripts/README_vector_db.md)
- [データエンリッチメントガイド](scripts/README_enrich_data.md)