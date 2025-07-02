# RPO自動化システム

AI・RPAツールを活用した採用代行業務（RPO）の自動化・効率化システム

## 概要

本システムは、Bizreachでの候補者スクリーニングから、AIによる採用要件マッチング判定、結果のレポーティングまでを自動化し、RPO業務の効率化を実現します。

## 主な機能

- **自動スクリーニング**: Bizreachから候補者情報を自動取得
- **AI判定**: 採用要件との適合性をAIが判定・スコアリング
- **構造化データ管理**: 候補者情報・採用要件をJSON形式で管理
- **レポート生成**: Google Sheetsへの自動出力
- **学習機能**: クライアントフィードバックを基にした判定精度向上

## システムアーキテクチャ

### 技術スタック

- **言語**: Python 3.9+
- **インフラ**: Google Cloud Platform (GCP)
- **データストア**: BigQuery
- **AI/ML**: 
  - Google Gemini (構造化・プロンプト生成)
  - OpenAI ChatGPT-4o (マッチング判定)
- **ブラウザ自動化**: Playwright
- **連携**: Google Sheets API, Google Docs API

### データフロー

1. **採用要件取得**: Google Docsから要件を取得しJSON構造化
2. **候補者検索**: Bizreachで自動検索・情報取得
3. **AI判定**: 要件と候補者のマッチング判定
4. **結果出力**: Google Sheetsへ結果を記録
5. **フィードバック**: クライアント判断を学習データとして活用

## プロジェクト構成

```
rpo-automation/
├── src/
│   ├── scraping/          # Bizreachスクレイピング
│   ├── ai/                # AI判定ロジック
│   ├── data/              # データ処理・構造化
│   ├── sheets/            # Google Sheets連携
│   └── utils/             # 共通ユーティリティ
├── config/                # 設定ファイル
├── tests/                 # テストコード
├── docs/                  # ドキュメント
└── scripts/               # 実行スクリプト
```

## セットアップ

### 前提条件

- Python 3.9以上
- GCPアカウント
- Google Workspace
- Bizreachアカウント

### インストール

```bash
# リポジトリのクローン
git clone https://github.com/[your-org]/rpo-automation.git
cd rpo-automation

# 仮想環境の作成
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 依存関係のインストール
pip install -r requirements.txt
```

### 環境設定

1. GCPプロジェクトの設定
```bash
gcloud init
gcloud config set project [YOUR_PROJECT_ID]
```

2. 環境変数の設定
```bash
cp .env.example .env
# .envファイルを編集して必要な情報を設定
```

### 必要な環境変数

- `GOOGLE_CLOUD_PROJECT`: GCPプロジェクトID
- `BIGQUERY_DATASET`: BigQueryデータセット名
- `OPENAI_API_KEY`: OpenAI APIキー
- `GEMINI_API_KEY`: Gemini APIキー
- `GOOGLE_SHEETS_ID`: 出力先のGoogle Sheets ID

## 使用方法

### 日次実行

```bash
python scripts/daily_screening.py --date 2024-01-01
```

### 個別機能の実行

```bash
# 採用要件の構造化
python -m src.data.structure_requirements --doc-id [GOOGLE_DOC_ID]

# 候補者スクリーニング
python -m src.scraping.bizreach_scraper --job-id [JOB_ID]

# AI判定実行
python -m src.ai.matching_engine --candidate-id [CANDIDATE_ID]
```

## 開発スケジュール

### Week 1: 基盤+コア機能（MVP）
- [ ] GCP環境構築、BigQuery設定
- [ ] Bizreachスクレイピング実装
- [ ] AI連携（Gemini＋ChatGPT-4o）

### Week 2: 実用化機能
- [ ] Google Sheets入出力
- [ ] 転記支援機能
- [ ] エラーハンドリング、日次バッチ設定

### Week 3: 改善+安定化
- [ ] フィードバック取込機能
- [ ] パフォーマンス調整
- [ ] 本番環境テスト

## テスト

```bash
# ユニットテスト
pytest tests/unit/

# 統合テスト
pytest tests/integration/

# カバレッジレポート
pytest --cov=src tests/
```

## デプロイ

```bash
# Cloud Functionsへのデプロイ
gcloud functions deploy daily-screening \
    --runtime python39 \
    --trigger-schedule "0 9 * * *" \
    --entry-point main
```

## 運用

### 監視

- Cloud Logging でエラーログを監視
- BigQuery で処理統計を確認

### トラブルシューティング

よくある問題と対処法は[docs/troubleshooting.md](docs/troubleshooting.md)を参照

## ライセンス

[ライセンスタイプを記載]

## 貢献

プルリクエストを歓迎します。大きな変更の場合は、まずissueを作成して変更内容を議論してください。

## サポート

問題や質問がある場合は、GitHubのissueを作成してください。