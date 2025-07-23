#!/usr/bin/env python3
"""
media_platformsテーブルにurl_patternsカラムを追加するスクリプト
"""
import os
import sys
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.utils.supabase_client import get_supabase_client

def add_url_patterns_column():
    """url_patternsカラムを追加"""
    supabase = get_supabase_client()
    
    # URL patterns for each platform
    url_patterns = {
        'bizreach': ['cr-support.jp', 'bizreach.jp'],
        'linkedin': ['linkedin.com'],
        'green': ['green-japan.com'],
        'wantedly': ['wantedly.com'],
        'doda': ['doda.jp'],
        'recruit_agent': ['r-agent.com'],
        'indeed': ['indeed.com', 'jp.indeed.com']
    }
    
    print("Updating media_platforms with url_patterns...")
    
    for name, patterns in url_patterns.items():
        try:
            response = supabase.table("media_platforms").update({
                "url_patterns": patterns
            }).eq("name", name).execute()
            
            if response.data:
                print(f"✅ Updated {name} with patterns: {patterns}")
            else:
                print(f"⚠️  No record found for {name}")
                
        except Exception as e:
            print(f"❌ Error updating {name}: {str(e)}")
    
    print("\nUpdate complete!")

if __name__ == "__main__":
    add_url_patterns_column()