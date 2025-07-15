# RPO Automation

採用プロセス自動化のための統合システム

## システム概要

このプロジェクトは、採用プロセスを効率化するための複数のシステムを統合したものです：

1. **AIマッチングシステム** - AIを活用した候補者と求人のマッチング
2. **Webアプリケーション** - 採用管理のためのWebインターフェース
3. **Chrome拡張機能** - 求人サイトからの候補者情報収集
4. **データ分析基盤** - BigQueryとSupabaseを活用したデータ管理

## プロジェクト構造

```
rpo-automation/
├── ai_matching_system/         # AIマッチングシステム
│   ├── README.md              # 使用方法とアーキテクチャ
│   ├── run_separated_matching.py
│   ├── sample_data/           # サンプルデータ
│   └── ai_matching/           # コアモジュール
│
├── webapp/                    # FastAPI Webアプリケーション
│   ├── main.py               # アプリケーションエントリーポイント
│   ├── routers/              # APIルーター
│   ├── templates/            # HTMLテンプレート
│   └── static/               # 静的ファイル
│
├── extension/                 # Chrome拡張機能
│   ├── manifest.json         # 拡張機能設定
│   ├── background/           # バックグラウンドスクリプト
│   ├── content/              # コンテンツスクリプト
│   └── popup/                # ポップアップUI
│
├── database/                  # データベース関連
│   ├── migrations/           # SQLマイグレーション
│   ├── bigquery/             # BigQuery関連
│   └── sql/                  # SQLスクリプト
│
├── core/                      # 共通コアモジュール
│   ├── agent/                # エージェントシステム
│   ├── ai/                   # AI関連（旧版）
│   ├── rag_agent/            # RAGエージェント
│   ├── scraping/             # スクレイピング
│   ├── services/             # 共通サービス
│   └── utils/                # ユーティリティ
│
├── cloud_functions/           # Google Cloud Functions
├── scripts/                   # ユーティリティスクリプト
├── docs/                      # ドキュメント
└── tests/                     # テスト
```

## クイックスタート

### 1. 環境設定

```bash
# 仮想環境の作成
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 依存関係のインストール
pip install -r requirements.txt
```

### 2. 環境変数の設定

```bash
cp .env.example .env
# .envファイルを編集して必要な環境変数を設定
```

### 3. 各システムの起動

#### AIマッチングシステム
```bash
cd ai_matching_system
export GEMINI_API_KEY='your-api-key'
python run_separated_matching.py
```
詳細は [ai_matching_system/README.md](ai_matching_system/README.md) を参照

#### Webアプリケーション
```bash
# 方法1: プロジェクトルートから
python3 run_webapp.py

# 方法2: webappディレクトリから
cd webapp
./run_webapp.sh
```

#### Chrome拡張機能
1. Chrome拡張機能管理ページを開く
2. 「デベロッパーモード」を有効化
3. 「パッケージ化されていない拡張機能を読み込む」
4. `extension/` フォルダを選択

## 主要機能

### AIマッチングシステム
- 候補者レジュメと求人要件の自動マッチング
- 必須要件の充足度評価（A/B/C/D）
- Web検索による追加情報収集
- 詳細な評価レポート生成

### Webアプリケーション
- 求人管理
- 候補者管理
- マッチング結果の閲覧
- ユーザー権限管理

### Chrome拡張機能
- 求人サイトからの候補者情報自動収集
- Bizreach対応
- バックグラウンド同期

## 開発者向け情報

### 必要な環境
- Python 3.8以上
- Node.js 14以上（Chrome拡張機能開発用）
- Google Cloud SDK（Cloud Functions使用時）

### APIキー
以下のAPIキーが必要です：
- Google Gemini API Key（AIマッチング用）
- Tavily API Key（Web検索用、オプション）
- Supabase認証情報（データベース用）

### テスト実行
```bash
pytest tests/
```

## ライセンス

[LICENSE](LICENSE) ファイルを参照してください。

## 貢献

プルリクエストを歓迎します。大きな変更の場合は、まずissueを作成して変更内容を説明してください。

## サポート

問題や質問がある場合は、GitHubのissueを作成してください。