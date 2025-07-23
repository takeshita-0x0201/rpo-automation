#!/usr/bin/env python3
"""
求人情報を構造化するスクリプト
Gemini 2.0 Pro モデルを使用
"""
import os
import json
from dotenv import load_dotenv

# 環境変数を読み込み
load_dotenv()

def process_job_description():
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
        
        # 改善したプロンプトファイルを読み込み
        with open('improved_structure_prompt.txt', 'r', encoding='utf-8') as f:
            prompt = f.read()
        
        # 利用可能なモデルを確認
        from google.generativeai import list_models
        
        print("利用可能なモデルを確認中...")
        for model_info in list_models():
            print(f"- {model_info.name}")
            
        # Gemini 1.5 Pro モデルを初期化（利用可能なモデルに変更）
        model = GenerativeModel('gemini-1.5-pro')
        
        print("Gemini 2.0 Pro モデルに求人情報を送信中...")
        
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
            
            # ファイルに保存
            with open('structured_job_data.json', 'w', encoding='utf-8') as f:
                json.dump(structured_data, f, ensure_ascii=False, indent=2)
                
            print("\n構造化データを structured_job_data.json に保存しました")
            
        except Exception as e:
            print(f"\nJSONの解析または保存中にエラーが発生しました: {e}")
        
    except ImportError:
        print("エラー: Google AI SDK (google-generativeai) がインストールされていません")
        print("インストール方法: pip install google-generativeai")
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("求人情報構造化スクリプト")
    print("=" * 50)
    process_job_description()