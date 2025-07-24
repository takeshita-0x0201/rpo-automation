#!/usr/bin/env python3
"""
環境変数セットアップスクリプト
.envファイルの作成をガイドします
"""

import os
import sys

def main():
    print("環境変数セットアップスクリプト")
    print("=" * 50)
    
    # 親ディレクトリのパスを取得
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_file_path = os.path.join(parent_dir, '.env')
    env_example_path = os.path.join(parent_dir, '.env.example')
    
    print(f"\n作業ディレクトリ: {parent_dir}")
    
    # .envファイルの存在確認
    if os.path.exists(env_file_path):
        print("\n✓ .envファイルが既に存在します")
        print("  既存の設定を確認してください")
        
        # 現在の設定を表示（キーの部分は隠す）
        with open(env_file_path, 'r') as f:
            lines = f.readlines()
            print("\n【現在の設定】")
            for line in lines:
                if '=' in line and not line.strip().startswith('#'):
                    key, value = line.strip().split('=', 1)
                    masked_value = '*' * min(len(value), 10) if value else '(未設定)'
                    print(f"  {key} = {masked_value}")
        return
    
    # .env.exampleファイルの確認
    if not os.path.exists(env_example_path):
        print("\n✗ .env.exampleファイルが見つかりません")
        print("  先に.env.exampleファイルを作成します...")
        
        example_content = """# Supabase Configuration
SUPABASE_URL=your_supabase_url_here
SUPABASE_KEY=your_supabase_anon_key_here

# API Keys
GEMINI_API_KEY=your_gemini_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here

# Optional: Debug Mode
DEBUG_MODE=false
"""
        
        with open(env_example_path, 'w') as f:
            f.write(example_content)
        print("  ✓ .env.exampleファイルを作成しました")
    
    # .envファイルの作成をガイド
    print("\n【.envファイルの作成方法】")
    print("1. 以下のコマンドを実行して.env.exampleをコピー:")
    print(f"   cp {env_example_path} {env_file_path}")
    
    print("\n2. 作成した.envファイルを編集して、実際の値を設定:")
    print(f"   編集コマンド例: nano {env_file_path}")
    
    print("\n3. 必要な設定値:")
    print("   - SUPABASE_URL: SupabaseプロジェクトのURL")
    print("   - SUPABASE_KEY: Supabaseのanonキー")
    print("   - GEMINI_API_KEY: Google AI StudioのAPIキー")
    print("   - TAVILY_API_KEY: Tavily検索APIキー（オプション）")
    
    print("\n【取得方法】")
    print("Supabase:")
    print("  1. https://app.supabase.com にログイン")
    print("  2. プロジェクトを選択")
    print("  3. Settings > API から URL と anon key を取得")
    
    print("\nGoogle AI Studio:")
    print("  1. https://makersuite.google.com/app/apikey にアクセス")
    print("  2. 'Create API key' をクリック")
    
    print("\nTavily (オプション):")
    print("  1. https://tavily.com にアクセス")
    print("  2. サインアップしてAPIキーを取得")
    
    print("\n【セキュリティ注意事項】")
    print("- .envファイルは絶対にGitにコミットしないでください")
    print("- .gitignoreに.envが含まれていることを確認してください")
    
    # .gitignoreの確認
    gitignore_path = os.path.join(parent_dir, '.gitignore')
    if os.path.exists(gitignore_path):
        with open(gitignore_path, 'r') as f:
            content = f.read()
            if '.env' in content:
                print("  ✓ .gitignoreに.envが含まれています")
            else:
                print("  ⚠️  .gitignoreに.envが含まれていません！追加してください")
    else:
        print("  ⚠️  .gitignoreファイルが見つかりません！作成してください")

if __name__ == "__main__":
    main()