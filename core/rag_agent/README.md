# RAGベース採用評価エージェント

過去の採用評価データを活用し、AIとWeb検索を組み合わせて候補者を自動評価するシステムです。

## 特徴

- 🔍 **RAG (Retrieval-Augmented Generation)**: 過去の評価データから類似事例を検索
- 🌐 **Web検索統合**: 不足情報を自動的にWeb検索で補完
- 🔄 **Human-in-the-Loop**: 人間のフィードバックで継続的に改善
- 📊 **可視化UI**: Streamlitベースの直感的なインターフェース

## アーキテクチャ

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  候補者データ    │────▶│   RAGエージェント  │────▶│   評価結果      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                              │        ▲
                              ▼        │
                        ┌─────────────────┐
                        │  ベクトルDB      │
                        │ (過去の評価)     │
                        └─────────────────┘
                              ▲
                              │
                        ┌─────────────────┐
                        │ 人間のレビュー   │
                        └─────────────────┘
```

## セットアップ

### 1. 環境変数の設定

```bash
cp .env.example .env
# .envファイルを編集してAPIキーを設定
```

必須の環境変数:
- `OPENAI_API_KEY`: OpenAI APIキー
- `SUPABASE_URL`: SupabaseプロジェクトURL
- `SUPABASE_ANON_KEY`: Supabase匿名キー

オプション:
- `SERPER_API_KEY`: Web検索用のSerper APIキー

### 2. 依存関係のインストール

```bash
pip install -r requirements.txt
```

### 3. ベクトルデータベースの初期化

```bash
python vector_db.py
```

## 使用方法

### Streamlit UIの起動

```bash
streamlit run review_ui.py
```

ブラウザが自動的に開き、`http://localhost:8501`でUIにアクセスできます。

### プログラマティックな使用

```python
from rag_agent.vector_db import RecruitmentVectorDB
from rag_agent.agent import RAGRecruitmentAgent

# 初期化
db = RecruitmentVectorDB()
agent = RAGRecruitmentAgent(db)

# 評価実行
job_requirement = {
    "title": "バックエンドエンジニア",
    "company": "株式会社サンプル",
    "required_skills": ["Python", "FastAPI", "AWS"],
    "preferred_skills": ["Docker", "Kubernetes"],
    "experience_years": "3年以上",
    "team_size": "5名",
    "salary_range": "600-800万円",
    "description": "ECサイトのバックエンド開発"
}

candidate_resume = {
    "name": "候補者A",
    "experience": "5年",
    "current_position": "シニアエンジニア",
    "skills": ["Python", "Django", "AWS", "Docker"],
    "work_history": "Web系企業でバックエンド開発に従事",
    "achievements": "マイクロサービス化プロジェクトをリード"
}

result = agent.evaluate_candidate(job_requirement, candidate_resume)
print(result)
```

## 主要コンポーネント

### 1. `vector_db.py`
- ChromaDBを使用したベクトルデータベース
- 過去の評価データの保存と検索
- OpenAI Embeddingsによるベクトル化

### 2. `agent.py`
- LangChainベースのRAGエージェント
- 類似事例検索とWeb検索の統合
- 4回までの反復的な情報収集

### 3. `feedback_loop.py`
- 人間のフィードバックを取り込む仕組み
- Supabaseとの連携
- 継続的な学習と改善

### 4. `review_ui.py`
- Streamlitベースの評価UI
- リアルタイムでの評価実行
- 履歴管理と統計表示

## 評価プロセス

1. **初回検索**: 過去の類似評価事例を検索
2. **情報補完**: 不足情報をWeb検索で補完
3. **反復改善**: 最大4回まで追加検索を実行
4. **スコアリング**: 0-100点とA-Dグレードで評価
5. **人間レビュー**: 最終的な判断と調整
6. **学習**: フィードバックをベクトルDBに保存

## 評価基準

- **必須スキルの充足度**: 各スキルを個別に評価
- **歓迎スキルの保有状況**: 加点要素として考慮
- **経験年数とレベル感**: 要件との適合性
- **チーム規模の経験**: マネジメント能力の評価
- **企業文化とのフィット**: Web検索で企業情報を調査
- **成長ポテンシャル**: 過去の実績から推測
- **給与期待値**: 市場相場との整合性

## トラブルシューティング

### ベクトルDBエラー
```bash
# データベースのリセット
python -c "from vector_db import RecruitmentVectorDB; db = RecruitmentVectorDB(); db.reset_database()"
```

### API制限エラー
- OpenAI APIの利用制限を確認
- `TEMPERATURE`や`MAX_ITERATIONS`を調整

### メモリ不足
- `CHROMA_PERSIST_DIRECTORY`のサイズを確認
- 古いデータの定期的なクリーンアップ

## 開発

### テスト実行
```bash
# 各モジュールのテスト
python vector_db.py
python agent.py
python feedback_loop.py
```

### デバッグモード
StreamlitUIで「開発者モード」を有効にすると、ベクトルDBのリセットなどの操作が可能です。

## ライセンス

このプロジェクトは内部使用のみを目的としています。