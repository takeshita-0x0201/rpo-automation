#!/usr/bin/env python3
"""
汎用的な求人情報構造化スクリプト
Gemini 1.5 Pro モデルを使用
"""
import os
import json
import argparse
from dotenv import load_dotenv

# 環境変数を読み込み
load_dotenv()

def process_job_description(job_description_path, job_memo_path, output_path=None):
    """求人情報を構造化する"""
    try:
        # Google AI SDKをインポート
        from google.generativeai import GenerativeModel, configure
        
        # APIキーを設定
        api_key = os.environ.get('GEMINI_API_KEY')
        if not api_key:
            print("エラー: GEMINI_API_KEY 環境変数が設定されていません")
            return
            
        configure(api_key=api_key)
        
        # 汎用プロンプトテンプレートを読み込み
        with open('generic_structure_prompt.txt', 'r', encoding='utf-8') as f:
            prompt_template = f.read()
        
        # 求人票を読み込み
        try:
            with open(job_description_path, 'r', encoding='utf-8') as f:
                job_description = f.read()
        except FileNotFoundError:
            print(f"エラー: 求人票ファイル '{job_description_path}' が見つかりません")
            return
        
        # 求人メモを読み込み
        try:
            with open(job_memo_path, 'r', encoding='utf-8') as f:
                job_memo = f.read()
        except FileNotFoundError:
            print(f"エラー: 求人メモファイル '{job_memo_path}' が見つかりません")
            return
        
        # プロンプトを作成
        prompt = prompt_template.replace("[求人票の内容]", job_description)
        prompt = prompt.replace("[求人メモの内容]", job_memo)
        
        model = GenerativeModel('gemini-2.5-flash')
        
        print("求人情報を分析中...")
        
        # モデルにプロンプトを送信
        response = model.generate_content(prompt)
        
        # 結果を表示
        print("\n=== 構造化された求人情報 ===\n")
        print(response.text)
        
        # 結果をJSONファイルとして保存
        try:
            # レスポンスからJSONを抽出
            json_text = response.text
            if "```json" in json_text:
                json_text = json_text.split("```json")[1].split("```")[0].strip()
            
            # JSONとして解析
            structured_data = json.loads(json_text)
            
            # 出力パスを決定
            if not output_path:
                output_path = "structured_job_data.json"
            
            # ファイルに保存
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(structured_data, f, ensure_ascii=False, indent=2)
                
            print(f"\n構造化データを {output_path} に保存しました")
            
        except Exception as e:
            print(f"\nJSONの解析または保存中にエラーが発生しました: {e}")
        
    except ImportError:
        print("エラー: Google AI SDK (google-generativeai) がインストールされていません")
        print("インストール方法: pip install google-generativeai")
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description='求人情報を構造化するスクリプト')
    parser.add_argument('job_description', help='求人票ファイルのパス')
    parser.add_argument('job_memo', help='求人メモファイルのパス')
    parser.add_argument('--output', '-o', help='出力JSONファイルのパス（デフォルト: structured_job_data.json）')
    
    args = parser.parse_args()
    
    print("求人情報構造化スクリプト")
    print("=" * 50)
    process_job_description(args.job_description, args.job_memo, args.output)

if __name__ == "__main__":
    main()