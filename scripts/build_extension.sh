#!/bin/bash

# Chrome拡張機能のビルドスクリプト
# 開発用とリリース用のビルドを作成

set -e

# カラー出力の定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# プロジェクトルートディレクトリ
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXTENSION_DIR="$PROJECT_ROOT/src/extension"
BUILD_DIR="$PROJECT_ROOT/build"
DIST_DIR="$PROJECT_ROOT/dist"

echo -e "${GREEN}Chrome拡張機能のビルドを開始します...${NC}"

# ビルドディレクトリを作成
echo "ビルドディレクトリを準備中..."
rm -rf "$BUILD_DIR" "$DIST_DIR"
mkdir -p "$BUILD_DIR" "$DIST_DIR"

# 拡張機能ファイルをコピー
echo "ファイルをコピー中..."
cp -r "$EXTENSION_DIR"/* "$BUILD_DIR/"

# 開発モードチェック
if [ "$1" == "--dev" ]; then
    echo -e "${YELLOW}開発モードでビルド中...${NC}"
    # 開発用の設定を適用（必要に応じて）
    BUILD_NAME="rpo-extension-dev"
else
    echo "プロダクションモードでビルド中..."
    BUILD_NAME="rpo-extension"
    
    # プロダクション用の最適化
    # デバッグコードの削除
    find "$BUILD_DIR" -name "*.js" -type f -exec sed -i '' '/DebugUtil\.log/d' {} \;
    find "$BUILD_DIR" -name "*.js" -type f -exec sed -i '' '/console\.log/d' {} \;
fi

# manifest.jsonのバージョンを更新（オプション）
if [ -n "$VERSION" ]; then
    echo "バージョンを $VERSION に更新中..."
    sed -i '' "s/\"version\": \"[0-9.]*\"/\"version\": \"$VERSION\"/" "$BUILD_DIR/manifest.json"
fi

# ZIPファイルを作成
echo "ZIPファイルを作成中..."
cd "$BUILD_DIR"
zip -r "$DIST_DIR/${BUILD_NAME}.zip" . -x "*.DS_Store" "*/.git/*"

# CRXファイルの生成（Chrome Web Store用）
if command -v chrome &> /dev/null; then
    echo "CRXファイルを生成中..."
    # Chrome実行ファイルのパスを検出
    if [ -f "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" ]; then
        CHROME_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    else
        CHROME_PATH="chrome"
    fi
    
    # 秘密鍵が存在しない場合は作成
    KEY_FILE="$PROJECT_ROOT/extension.pem"
    if [ ! -f "$KEY_FILE" ]; then
        echo "秘密鍵を生成中..."
        "$CHROME_PATH" --pack-extension="$BUILD_DIR"
        mv "$BUILD_DIR.pem" "$KEY_FILE"
        mv "$BUILD_DIR.crx" "$DIST_DIR/${BUILD_NAME}.crx"
    else
        "$CHROME_PATH" --pack-extension="$BUILD_DIR" --pack-extension-key="$KEY_FILE"
        mv "$BUILD_DIR.crx" "$DIST_DIR/${BUILD_NAME}.crx"
    fi
fi

# ビルド情報を表示
echo -e "\n${GREEN}ビルド完了！${NC}"
echo -e "出力ディレクトリ: ${YELLOW}$DIST_DIR${NC}"
echo -e "ZIPファイル: ${YELLOW}${BUILD_NAME}.zip${NC}"

if [ -f "$DIST_DIR/${BUILD_NAME}.crx" ]; then
    echo -e "CRXファイル: ${YELLOW}${BUILD_NAME}.crx${NC}"
fi

# ファイルサイズを表示
echo -e "\nファイルサイズ:"
ls -lh "$DIST_DIR"/${BUILD_NAME}.*

# インストール手順を表示
echo -e "\n${YELLOW}インストール方法:${NC}"
echo "1. Chromeで chrome://extensions/ を開く"
echo "2. 「デベロッパーモード」を有効にする"
echo "3. 「パッケージ化されていない拡張機能を読み込む」をクリック"
echo "4. $BUILD_DIR ディレクトリを選択"
echo -e "\nまたは、${YELLOW}${BUILD_NAME}.zip${NC} をドラッグ&ドロップしてインストール"

# クリーンアップオプション
if [ "$2" == "--clean" ]; then
    echo -e "\n${YELLOW}ビルドディレクトリをクリーンアップ中...${NC}"
    rm -rf "$BUILD_DIR"
fi