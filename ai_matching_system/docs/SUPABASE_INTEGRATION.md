# Supabase統合ガイド

## 概要
AIマッチングシステムにSupabaseのcandidatesテーブルから候補者情報を取得する機能を追加しました。

## 設定

### 1. 環境変数の設定
`.env`ファイルに以下の変数を追加してください：

```env
# Supabase Configuration
SUPABASE_URL=your_supabase_url_here
SUPABASE_KEY=your_supabase_anon_key_here
```

### 2. 依存関係のインストール
```bash
pip install -r requirements.txt
```

## 使用方法

### 基本的な使用例

```python
from ai_matching.nodes.orchestrator import DeepResearchOrchestrator

# オーケストレーターの初期化
orchestrator = DeepResearchOrchestrator(
    gemini_api_key="your_gemini_api_key",
    tavily_api_key="your_tavily_api_key"  # オプション
)

# マッチング実行（candidate_idを指定）
result = await orchestrator.run(
    resume=resume_text,
    job_description=job_description_text,
    job_memo=job_memo_text,
    candidate_id="A12345678"  # Supabaseのcandidate_id
)
```

### 候補者IDの指定方法

1. **直接指定**: `candidate_id`パラメータで指定
2. **レジュメから抽出**: レジュメの最初の5行に`ID: A12345678`のような形式で記載

## 取得される候補者情報

以下の情報がSupabaseから取得され、評価に使用されます：

- **年齢**: 候補者の年齢
- **性別**: 候補者の性別（利用可能な場合）
- **現在の所属**: 現在の会社名
- **在籍企業数**: これまでの転職回数

## 出力例

評価プロンプトに以下のような情報が追加されます：

```
## 候補者情報
年齢: 35歳
性別: 男性
現在の所属: 株式会社Example
在籍企業数: 3社
```

## エラーハンドリング

Supabase接続が失敗した場合でも、マッチング処理は継続されます：
- 接続エラー: `年齢: 不明（エラーが発生しました）`
- データなし: `年齢: 不明（データが見つかりません）`
- IDなし: `年齢: 不明（候補者IDが見つかりません）`

## トラブルシューティング

### 1. Supabaseに接続できない
- 環境変数が正しく設定されているか確認
- Supabase URLとAPIキーが有効か確認

### 2. 候補者データが取得できない
- candidate_idが正しいか確認
- candidatesテーブルに該当データが存在するか確認

### 3. 認証エラー
- APIキーの権限を確認（candidatesテーブルのSELECT権限が必要）