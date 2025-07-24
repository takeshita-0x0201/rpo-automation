# デバッグツール

このディレクトリには、AIマッチングシステムのデバッグに役立つツールが含まれています。

## 候補者情報デバッグツール

`debug_candidate_info.py` は、候補者情報の取得と表示を行うデバッグツールです。年齢が「不明」と表示される問題を診断するのに役立ちます。

### 前提条件

- Python 3.7以上
- 必要なパッケージ: `supabase`, `python-dotenv`
- 環境変数: `SUPABASE_URL`, `SUPABASE_KEY`

### インストール

```bash
pip install supabase python-dotenv
```

### 使い方

```bash
# データベース接続確認
python scripts/debug_candidate_info.py --check-db

# 最近の候補者一覧を表示
python scripts/debug_candidate_info.py --list

# 候補者IDで情報を取得
python scripts/debug_candidate_info.py --id <candidate_id>

# レジュメファイルから候補者情報を取得
python scripts/debug_candidate_info.py --resume <resume_file_path>

# EvaluatorNodeの_get_candidate_infoメソッドをテスト
python scripts/debug_candidate_info.py --test-evaluator --id <candidate_id>
python scripts/debug_candidate_info.py --test-evaluator --resume <resume_file_path>
```

### 診断手順

1. まず、データベース接続を確認します：
   ```bash
   python scripts/debug_candidate_info.py --check-db
   ```

2. 最近の候補者一覧を表示して、有効な候補者IDを確認します：
   ```bash
   python scripts/debug_candidate_info.py --list
   ```

3. 特定の候補者IDで情報を取得します：
   ```bash
   python scripts/debug_candidate_info.py --id <candidate_id>
   ```

4. レジュメファイルから候補者情報を取得します：
   ```bash
   python scripts/debug_candidate_info.py --resume sample_data/resume.txt
   ```

5. EvaluatorNodeの処理をシミュレートして問題を診断します：
   ```bash
   python scripts/debug_candidate_info.py --test-evaluator --resume sample_data/resume.txt
   ```

### 問題の一般的な原因

1. **候補者IDが見つからない**：
   - レジュメに候補者IDが含まれていない
   - IDの形式が想定と異なる（例：`ID:` の後にスペースがない）

2. **データベース接続の問題**：
   - 環境変数が正しく設定されていない
   - Supabaseへの接続に失敗している

3. **データが存在しない**：
   - 候補者IDは正しいが、データベースに該当するレコードがない
   - テーブル構造が想定と異なる（カラム名が異なるなど）

### 解決策

1. **レジュメにIDを明示的に追加**：
   レジュメの先頭に以下の形式でIDを追加します：
   ```
   ID: candidate_12345
   ```

2. **環境変数の確認**：
   `.env` ファイルに以下の設定があることを確認します：
   ```
   SUPABASE_URL=https://your-project-url.supabase.co
   SUPABASE_KEY=your-supabase-key
   ```

3. **データベースの確認**：
   Supabaseコンソールで `candidates` テーブルに以下のカラムがあることを確認します：
   - `candidate_id`
   - `age`
   - `gender`
   - `candidate_company`
   - `enrolled_company_count`