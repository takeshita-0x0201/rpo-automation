# APIキー設定ガイド

## 設定方法

APIキーの設定には以下の3つの方法があります：

### 方法1: 環境変数として設定（推奨）

ターミナルで以下のコマンドを実行：

```bash
# Gemini APIキー（必須）
export GEMINI_API_KEY='your-gemini-api-key-here'

# Tavily APIキー（オプション）
export TAVILY_API_KEY='your-tavily-api-key-here'
```

**メリット**: セキュアで一時的な設定
**デメリット**: ターミナルを閉じると設定が消える

### 方法2: .envファイルを使用（開発環境推奨）

1. `.env.example`をコピーして`.env`を作成：
```bash
cp .env.example .env
```

2. `.env`ファイルを編集してAPIキーを設定：
```
# 既存の設定は残しておく
GEMINI_API_KEY=your-actual-gemini-api-key
TAVILY_API_KEY=your-actual-tavily-api-key
```

3. Pythonコードで環境変数を読み込む（必要に応じて）：
```python
from dotenv import load_dotenv
import os

load_dotenv()  # .envファイルを読み込む

gemini_key = os.getenv('GEMINI_API_KEY')
tavily_key = os.getenv('TAVILY_API_KEY')
```

**メリット**: 永続的な設定、プロジェクト固有の管理
**デメリット**: .envファイルをGitにコミットしないよう注意が必要

### 方法3: シェルの設定ファイルに追加（永続化）

bashの場合（~/.bashrcまたは~/.bash_profile）：
```bash
echo 'export GEMINI_API_KEY="your-gemini-api-key"' >> ~/.bashrc
echo 'export TAVILY_API_KEY="your-tavily-api-key"' >> ~/.bashrc
source ~/.bashrc
```

zshの場合（~/.zshrc）：
```bash
echo 'export GEMINI_API_KEY="your-gemini-api-key"' >> ~/.zshrc
echo 'export TAVILY_API_KEY="your-tavily-api-key"' >> ~/.zshrc
source ~/.zshrc
```

**メリット**: 永続的でシステム全体で利用可能
**デメリット**: 他のプロジェクトにも影響する可能性

## APIキーの取得方法

### Gemini APIキー（必須）
1. [Google AI Studio](https://makersuite.google.com/app/apikey)にアクセス
2. Googleアカウントでログイン
3. 「Get API key」をクリック
4. 新しいAPIキーを作成またはコピー

### Tavily APIキー（オプション）
1. [Tavily](https://tavily.com/)にアクセス
2. アカウントを作成（無料）
3. [Dashboard](https://app.tavily.com/)にログイン
4. API Keysセクションからキーをコピー

**注意**: Tavily無料プランは月1000リクエストまで

## 設定の確認

設定が正しくされているか確認：

```bash
# 環境変数の確認
echo $GEMINI_API_KEY
echo $TAVILY_API_KEY

# Pythonで確認
python -c "import os; print('Gemini:', os.getenv('GEMINI_API_KEY', 'Not set')[:10]+'...')"
python -c "import os; print('Tavily:', os.getenv('TAVILY_API_KEY', 'Not set')[:10]+'...')"
```

## セキュリティ注意事項

1. **APIキーを公開しない**
   - GitHubにコミットしない
   - .gitignoreに`.env`が含まれていることを確認
   
2. **APIキーの管理**
   - 定期的にローテーション
   - 不要になったキーは削除
   
3. **本番環境では**
   - Google Cloud Secret Manager
   - 環境変数管理サービスを使用

## トラブルシューティング

### APIキーが認識されない場合

1. 環境変数が正しく設定されているか確認
2. ターミナルを再起動してみる
3. Pythonスクリプトの実行ディレクトリを確認

### .envファイルが読み込まれない場合

```bash
# python-dotenvのインストール
pip install python-dotenv
```

### 権限エラーが出る場合

APIキーが正しいか、有効期限が切れていないか確認してください。