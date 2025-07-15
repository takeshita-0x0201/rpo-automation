# 既存データのAI評価スクリプト

## 概要
CSVファイルに記載されたレジュメテキストを読み込み、AIエージェントで評価を実行します。

## 使用方法

### 1. 環境変数の設定
```bash
export GEMINI_API_KEY="your-gemini-api-key"
export TAVILY_API_KEY="your-tavily-api-key"  # オプション
```

### 2. CSVファイルの準備
以下の形式でCSVファイルを作成：

```csv
id,resumeText,management_number,client_evaluation,client_comment
001,"経歴の詳細テキスト...",MGT-2024-001,D,"経験浅すぎて厳しそう"
002,"別の候補者の経歴...",MGT-2024-002,B,"財務経験は評価できる"
```

必須カラム:
- `id`: ケースの一意識別子
- `resumeText`: レジュメの全文テキスト

オプションカラム:
- `management_number`: 管理番号
- `client_evaluation`: クライアントの評価（A/B/C/D）
- `client_comment`: クライアントのコメント

### 3. 実行

```bash
# 基本的な使い方
python enrich_historical_data.py \
    sample_resumes.csv \
    "Treasury Specialist" \
    ../sample_data/job_description.txt \
    ../sample_data/job_memo.txt

# オプション付き
python enrich_historical_data.py \
    sample_resumes.csv \
    "Treasury Specialist" \
    ../sample_data/job_description.txt \
    ../sample_data/job_memo.txt \
    --limit 10 \
    --batch-size 3 \
    --output treasury_evaluations.json

# ドライラン（実行せずに対象を確認）
python enrich_historical_data.py \
    sample_resumes.csv \
    "Treasury Specialist" \
    ../sample_data/job_description.txt \
    ../sample_data/job_memo.txt \
    --dry-run
```

### 4. 出力

評価結果は以下の形式でJSONファイルに保存されます：

```json
{
  "evaluated_at": "2024-01-15T10:00:00",
  "position": "Treasury Specialist",
  "job_description_path": "path/to/job_description.txt",
  "job_memo_path": "path/to/job_memo.txt",
  "total_resumes": 3,
  "evaluations": [
    {
      "case_id": "001",
      "management_number": "MGT-2024-001",
      "position": "Treasury Specialist",
      "ai_evaluation": {
        "recommendation": "D",
        "score": 25,
        "confidence": "高",
        "reasoning": "Treasury経験なし",
        "strengths": ["経理基礎知識"],
        "concerns": ["専門経験不足"],
        "overall_assessment": "...",
        "evaluated_at": "2024-01-15T10:00:00"
      },
      "client_evaluation": "D",
      "comparison": {
        "match": true,
        "client": "D",
        "ai": "D"
      }
    }
  ]
}
```

同時に以下のファイルも生成されます：
- 分析レポート（`*_report.json`）
- 評価結果CSV（`*_results.csv`）

評価結果CSVの形式：
```csv
id,management_number,ai_evaluation,reasoning,client_evaluation,client_comment,match
001,MGT-2024-001,D,Treasury特化経験なし、システム開発経験なし,D,経験浅すぎて厳しそう,○
002,MGT-2024-002,B,財務経験豊富、Python活用実績あり,B,財務経験は評価できるが、Treasury特化経験が不明,○
```

## 注意事項

- レジュメファイルは実際に存在する必要があります
- API制限を考慮してバッチサイズを調整してください
- 大量のレジュメを処理する場合は `--limit` オプションでテストしてから実行することを推奨