#!/usr/bin/env python3
"""
media_platformsテーブルをセットアップするスクリプト
"""
import os
import sys
from dotenv import load_dotenv

# プロジェクトのルートディレクトリをPythonパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.utils.supabase_client import get_supabase_client

def setup_media_platforms():
    """media_platformsテーブルの作成とデータ投入"""
    print("=== Setting up Media Platforms ===\n")
    
    try:
        # Supabaseクライアントを取得
        supabase = get_supabase_client()
        print("✓ Connected to Supabase\n")
        
        # 初期データ
        platforms_data = [
            {
                "name": "bizreach",
                "display_name": "ビズリーチ",
                "description": "即戦力人材の転職サイト",
                "url_patterns": ["cr-support.jp", "bizreach.jp"],
                "sort_order": 1,
                "is_active": True
            },
            {
                "name": "linkedin",
                "display_name": "LinkedIn",
                "description": "ビジネス特化型SNS",
                "url_patterns": ["linkedin.com"],
                "sort_order": 2,
                "is_active": True
            },
            {
                "name": "green",
                "display_name": "Green",
                "description": "IT/Web業界の転職サイト",
                "url_patterns": ["green-japan.com"],
                "sort_order": 3,
                "is_active": True
            },
            {
                "name": "wantedly",
                "display_name": "Wantedly",
                "description": "やりがいでつながる転職サイト",
                "url_patterns": ["wantedly.com"],
                "sort_order": 4,
                "is_active": True
            },
            {
                "name": "doda",
                "display_name": "doda",
                "description": "転職求人サイト",
                "url_patterns": ["doda.jp"],
                "sort_order": 5,
                "is_active": True
            },
            {
                "name": "recruit_agent",
                "display_name": "リクルートエージェント",
                "description": "転職エージェントサービス",
                "url_patterns": ["r-agent.com"],
                "sort_order": 6,
                "is_active": True
            },
            {
                "name": "indeed",
                "display_name": "Indeed",
                "description": "求人検索エンジン",
                "url_patterns": ["indeed.com", "jp.indeed.com"],
                "sort_order": 7,
                "is_active": True
            },
            {
                "name": "other",
                "display_name": "その他",
                "description": "その他の媒体",
                "url_patterns": [],
                "sort_order": 99,
                "is_active": True
            }
        ]
        
        # 既存のデータをチェック
        print("Checking existing data...")
        existing = supabase.table("media_platforms").select("name").execute()
        existing_names = [p['name'] for p in existing.data] if existing.data else []
        
        # データを挿入
        inserted_count = 0
        updated_count = 0
        
        for platform in platforms_data:
            try:
                if platform['name'] in existing_names:
                    # 既存レコードを更新
                    print(f"Updating {platform['display_name']}...")
                    supabase.table("media_platforms").update({
                        "display_name": platform['display_name'],
                        "description": platform['description'],
                        "url_patterns": platform['url_patterns'],
                        "sort_order": platform['sort_order'],
                        "is_active": platform['is_active']
                    }).eq("name", platform['name']).execute()
                    updated_count += 1
                else:
                    # 新規レコードを挿入
                    print(f"Inserting {platform['display_name']}...")
                    supabase.table("media_platforms").insert(platform).execute()
                    inserted_count += 1
                    
            except Exception as e:
                print(f"  ✗ Error with {platform['name']}: {str(e)}")
                
        print(f"\n✓ Setup complete!")
        print(f"  - Inserted: {inserted_count} platforms")
        print(f"  - Updated: {updated_count} platforms")
        
        # 最終確認
        print("\nVerifying data...")
        final_check = supabase.table("media_platforms").select("*").order("sort_order").execute()
        if final_check.data:
            print(f"✓ Total platforms in database: {len(final_check.data)}")
            for p in final_check.data:
                print(f"  - {p['display_name']} (active: {p['is_active']})")
        
    except Exception as e:
        print(f"✗ Setup failed: {str(e)}")
        print("\nPossible issues:")
        print("  1. media_platforms table doesn't exist")
        print("  2. Database connection failed")
        print("  3. Insufficient permissions")
        print("\nPlease ensure the table exists by running:")
        print("  database/scripts/create_media_platforms_table.sql")

if __name__ == "__main__":
    # .envファイルを読み込む
    load_dotenv()
    
    # セットアップ実行
    setup_media_platforms()