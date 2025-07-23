# RPO自動化システム（Chrome拡張機能版）

AI・RPAツールを活用した採用代行業務（RPO）の自動化・効率化システム

## 概要

本システムは、RPO事業者がクライアント企業に代わってBizreachでの候補者スクリーニング、AIによる採用要件マッチング、結果のレポーティングまでを自動化するシステムです。貸与PCからのアクセスしか許可されないといったセキュリティ制約にも対応できる**Chrome拡張機能によるスクレイピング**と、クラウドでの**AI判定・データ管理**を組み合わせた、柔軟な構成でRPO業務の効率化を実現します。

### システム利用者
- **管理者（Admin）**: システム全体の管理、ユーザー管理、設定管理
- **マネージャー（Manager）**: クライアント管理、採用要件管理、ジョブ実行
- **一般ユーザー（User）**: 結果の閲覧のみ
- **クライアント企業**: 採用要件を提供し、結果を受け取る（システムに直接アクセスしない）

## 主な機能

### コア機能
- **WebAppによる簡単操作**: ブラウザから採用要件の登録・実行・確認が可能
- **Chrome拡張機能による自動スクリーニング**: Bizreachから候補者情報を自動取得
- **AI判定**: 採用要件との適合性をAIが判定・スコアリング
- **構造化データ管理**: 候補者情報・採用要件をJSON形式で管理
- **レポート生成**: Google Sheetsへの自動出力

### 差別化機能
- **テキストベース採用要件入力**: クライアントから受け取った要件をそのまま入力可能
- **AIによる自動構造化**: 自然言語の要件をGemini APIでJSON化
- **ブラウザ完結型スクレイピング**: Chrome拡張機能による安全なデータ収集（実装済み）
- **リアルタイム進捗表示**: Chrome拡張機能での視覚的フィードバック
- **DeepResearchアルゴリズム**: 反復的なAIマッチングによる高精度な候補者評価（計画中）
- **ロールベースアクセス制御**: 役割に応じた機能制限で安全な運用

## システム構成

```mermaid
graph TD
    subgraph "ユーザーインターフェース"
        A[RPOスタッフ]
        B[WebApp<br/>Cloud Run]
    end
    
    subgraph "クラウド環境"
        C[FastAPI<br/>統一API]
        D[Supabase<br/>メタデータ管理]
        E[Gemini API<br/>要件構造化]
        F[AI判定<br/>候補者マッチング]
    end
    
    subgraph "実行環境（貸与PC）"
        H[Chrome拡張機能]
        I[Bizreach]
    end
    
    subgraph "結果確認"
        J[Google Sheets]
    end
    
    A -->|1: 要件登録| B
    B -->|2: 要件構造化| F
    A -->|3: 拡張機能でデータ収集| H
    H -->|4: スクレイピング| I
    H -->|5: データ送信| C
    C -->|6: データ保存| D
    A -->|7: AIマッチング実行| B
    B -->|8: ジョブ作成| C
    C -->|9: AI判定依頼| F
    F -->|10: 判定実行| E
    F -->|11: 結果保存| D
    F -->|12: レポート出力| J
    B -->|13: 結果表示| A
```

## クイックスタート

### 前提条件

- Python 3.9以上
- Supabaseアカウント
- Google Cloud Platform (Gemini API用)
- Google Workspace
- Bizreachアカウント
- Google Chrome

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

### 基本設定

1. 環境変数の設定
```bash
cp .env.example .env
# .envファイルを編集して必要な情報を設定
```

必要な環境変数:
- `SUPABASE_URL`: SupabaseプロジェクトのURL
- `SUPABASE_KEY`: Supabaseのサービスキー
- `GEMINI_API_KEY`: Google Gemini APIキー
- `JWT_SECRET_KEY`: JWT認証用のシークレットキー

2. WebAppの起動
```bash
cd src/web
uvicorn main:app --reload --port 8000
```

3. ブラウザでアクセス
```
http://localhost:8000
```

## 使用方法

### 1. 採用要件の登録
1. WebAppにログイン（管理者またはマネージャー権限）
2. 「採用要件管理」画面で新規登録
3. クライアントを選択
4. テキストベースで要件を入力（自然言語対応）
5. Gemini APIが自動で構造化処理

### 2. 候補者データの収集
1. Bizreachにログイン
2. Chrome拡張機能を起動
3. クライアントを選択
4. Bizreachで検索を実行
5. 「スクレイピング開始」で自動収集

### 3. AI判定の実行
1. WebAppの「ジョブ管理」画面へ
2. 「新規ジョブ作成」をクリック
3. 採用要件とデータソースを選択
4. ジョブを作成（ステータス: pending）
5. ジョブ一覧から「実行」をクリック
6. 結果をGoogle Sheetsで確認

## ドキュメント

### 設計・アーキテクチャ
- [システムアーキテクチャ](docs/architecture.md) - 全体設計と技術構成
- [データベース設計](docs/database-design.md) - Supabaseの詳細設計
- [AIマッチング設計](docs/ai-matching-deepresearch-design.md) - DeepResearchアルゴリズムの設計

### セットアップガイド
- [環境設定](docs/setup/environment.md) - 基本的な開発環境の構築
- [Supabaseセットアップ](docs/setup/supabase.md) - Supabaseプロジェクトの設定
- [Chrome拡張機能セットアップ](docs/setup/chrome-extension.md) - 拡張機能の開発・配布
- [データベース移行ガイド](docs/supabase-to-bigquery-migration.md) - 将来的なBigQuery移行手順

### 開発ガイド
- [WBS（作業計画書）](docs/development/wbs.md) - 段階的な開発計画
- [テストガイド](docs/development/testing.md) - テスト実行とカバレッジ
- [デプロイガイド](docs/development/deployment.md) - 本番環境への配布

### API仕様
- [API リファレンス](docs/api/reference.md) - FastAPI エンドポイントの詳細

### 運用ガイド
- [監視・メンテナンス](docs/operations/monitoring.md) - システム監視とログ確認
- [トラブルシューティング](docs/operations/troubleshooting.md) - よくある問題と対処法

## プロジェクト構成

```
rpo-automation/
├── src/
│   ├── web/                 # WebApp (FastAPI)
│   │   ├── routers/         # APIエンドポイント
│   │   ├── templates/       # HTMLテンプレート
│   │   └── static/          # 静的ファイル
│   ├── services/            # ビジネスロジック
│   │   ├── auth.py          # 認証サービス
│   │   ├── ai_service.py    # AI連携サービス
│   │   └── candidate_counter.py # 候補者カウント
│   └── extension/           # Chrome拡張機能
├── migrations/              # データベースマイグレーション
├── docs/                    # ドキュメント
├── tests/                   # テストコード
└── requirements.txt         # Pythonライブラリ
```

## 技術スタック

- **言語**: Python 3.9+, JavaScript/TypeScript
- **Webフレームワーク**: FastAPI, Jinja2テンプレート
- **データベース**: Supabase (PostgreSQL) - 全データを統合管理
- **AI/ML**: 
  - Google Gemini API - 採用要件の構造化
  - AIマッチング機能（実装予定）
- **認証**: JWT (JSON Web Tokens)
- **フロントエンド**: Bootstrap 5, Vanilla JavaScript
- **ブラウザ拡張**: Chrome Extension API (Manifest V3)
- **連携**: Google Sheets API

## ライセンス

[ライセンスタイプを記載]

## 貢献

プルリクエストを歓迎します。大きな変更の場合は、まずissueを作成して変更内容を議論してください。

## サポート

問題や質問がある場合は、GitHubのissueを作成してください。