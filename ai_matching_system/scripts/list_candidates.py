#!/usr/bin/env python3
"""
Supabaseのcandidatesテーブルから候補者情報を一覧表示
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

# 環境変数を読み込む
current_path = Path(__file__).resolve()
for parent in [current_path.parent.parent.parent]:
    env_path = parent / '.env'
    if env_path.exists():
        print(f"✅ .envファイルを発見: {env_path}")
        load_dotenv(env_path)
        break

def list_candidates(limit: int = 10):
    """candidatesテーブルから候補者情報を表示"""
    
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    
    if not url or not key:
        print("❌ Supabase認証情報が設定されていません")
        return
    
    try:
        client = create_client(url, key)
        
        # 候補者情報を取得
        response = client.table('candidates').select(
            'candidate_id, candidate_company, age, enrolled_company_count, gender'
        ).limit(limit).execute()
        
        if response.data:
            print(f"\n=== 候補者一覧 ({len(response.data)}件) ===")
            print("-" * 100)
            print(f"{'候補者ID':<15} {'現在の所属':<30} {'年齢':<6} {'性別':<6} {'在籍企業数':<10}")
            print("-" * 100)
            
            for candidate in response.data:
                candidate_id = candidate.get('candidate_id', '不明')
                company = candidate.get('candidate_company', '不明')[:28]  # 長い場合は切り詰め
                age = candidate.get('age', '不明')
                gender = candidate.get('gender', '不明')
                enrolled_count = candidate.get('enrolled_company_count', '不明')
                
                print(f"{candidate_id:<15} {company:<30} {age:<6} {gender:<6} {enrolled_count:<10}")
            
            print("-" * 100)
            
            # 全件数を取得
            count_response = client.table('candidates').select('*', count='exact').execute()
            total_count = count_response.count if hasattr(count_response, 'count') else len(response.data)
            
            if total_count > limit:
                print(f"\n全{total_count}件中、最初の{limit}件を表示しています")
                print(f"すべて表示するには: python {__file__} all")
                
        else:
            print("⚠️  candidatesテーブルにデータがありません")
            
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")

def get_candidate_by_id(candidate_id: str):
    """特定の候補者情報を詳細表示"""
    
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    
    if not url or not key:
        print("❌ Supabase認証情報が設定されていません")
        return
    
    try:
        client = create_client(url, key)
        
        response = client.table('candidates').select('*').eq('candidate_id', candidate_id).execute()
        
        if response.data and len(response.data) > 0:
            candidate = response.data[0]
            print(f"\n=== 候補者詳細情報: {candidate_id} ===")
            print(f"候補者ID: {candidate.get('candidate_id', '不明')}")
            print(f"現在の所属: {candidate.get('candidate_company', '不明')}")
            print(f"年齢: {candidate.get('age', '不明')}")
            print(f"性別: {candidate.get('gender', '不明')}")
            print(f"在籍企業数: {candidate.get('enrolled_company_count', '不明')}")
            
            # その他のフィールドも表示
            exclude_fields = ['candidate_id', 'candidate_company', 'age', 'gender', 'enrolled_company_count']
            other_fields = {k: v for k, v in candidate.items() if k not in exclude_fields and v is not None}
            
            if other_fields:
                print("\n--- その他の情報 ---")
                for key, value in other_fields.items():
                    print(f"{key}: {value}")
                    
        else:
            print(f"❌ 候補者ID '{candidate_id}' が見つかりません")
            
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "all":
            list_candidates(1000)  # 最大1000件まで表示
        else:
            # 特定の候補者IDを指定
            get_candidate_by_id(sys.argv[1])
    else:
        # デフォルトは10件表示
        list_candidates(10)