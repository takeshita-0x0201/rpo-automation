# ベクトルデータベース実装ガイド

## 概要
過去の評価データをベクトル化し、新規候補者の評価精度を向上させるためのRAGシステムです。

## セットアップ

### 1. 必要な環境変数
```bash
export GEMINI_API_KEY="your-gemini-api-key"
export PINECONE_API_KEY="your-pinecone-api-key"
```

### 2. Pineconeアカウントの設定
1. [Pinecone](https://www.pinecone.io/)でアカウントを作成
2. APIキーを取得
3. 無料プランで開始可能（768次元、100万ベクトルまで）

### 3. 依存関係のインストール
```bash
pip install -r requirements.txt
```

## 使用方法

### 1. 過去データのベクトル化
既存の評価データをベクトル化してPineconeに保存します。

```bash
# 基本的な使用方法
python scripts/vectorize_historical_data.py evaluation_results.json

# 求人情報ファイルを指定
python scripts/vectorize_historical_data.py evaluation_results.json \
  --job-desc sample_data/job_description.txt \
  --job-memo sample_data/job_memo.txt
```

#### ベクトル化の仕組み
各評価ケースから3種類のベクトルを生成：
- **combined_vector**: 求人情報＋候補者情報＋評価結果の結合
- **job_side_vector**: 求人情報のみ
- **candidate_vector**: 候補者情報＋評価結果

### 2. 類似ケースの検索
新規候補者に対して過去の類似ケースを検索します。

```bash
python scripts/search_similar_cases.py \
  sample_data/resume.txt \
  sample_data/job_description.txt \
  sample_data/job_memo.txt
```

#### 出力内容
- 最も類似したケース（類似度スコア付き）
- クライアント評価の傾向分析
- リスク要因の特定
- 推奨アクション

## データ構造

### 入力データ（evaluation_results.json）
```json
{
  "position": "財務・経理",
  "evaluations": [
    {
      "case_id": "req-006",
      "management_number": "BU6072253",
      "ai_evaluation": {
        "recommendation": "C",
        "score": 45,
        "reasoning": "経理シェアード業務2年..."
      },
      "client_evaluation": "D",
      "client_comment": "経験浅すぎて厳しそう",
      "comparison": {
        "match": false
      }
    }
  ]
}
```

### Pineconeメタデータ
```python
{
  "case_id": "req-006_BU6072253",
  "position": "財務・経理",
  "ai_recommendation": "C",
  "client_evaluation": "D",
  "client_comment": "経験浅すぎて厳しそう",
  "score": 45,
  "reasoning": "経理シェアード業務2年...",
  "vector_type": "combined",
  "evaluation_match": False,
  "created_at": "2025-01-15T10:00:00"
}
```

## 活用例

### 1. 評価精度の向上
- 類似ケースでクライアントがNGとした理由を参考に
- AIの過大評価を防ぐ

### 2. リスク要因の早期発見
- 「システム面厳しそう」など頻出する懸念点を事前に把握
- 特定のパターンでミスマッチが多い場合は注意

### 3. 評価基準の学習
- クライアントの暗黙の評価基準を発見
- プロンプトの継続的改善に活用

## トラブルシューティング

### "Index not found"エラー
初回実行時は自動的にインデックスが作成されます。
作成に10秒程度かかるため、しばらく待ってください。

### 埋め込み生成エラー
- Gemini APIキーが正しく設定されているか確認
- APIの利用制限に達していないか確認

### Pinecone接続エラー
- Pinecone APIキーが正しいか確認
- ネットワーク接続を確認

## 今後の拡張
1. 評価結果のフィードバックループ
2. リアルタイムでの類似ケース提示
3. 評価基準の自動調整