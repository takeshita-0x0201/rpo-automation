#!/usr/bin/env python3
"""
同期データをリセットして再同期できるようにする
"""
import os
from supabase import create_client
from pinecone import Pinecone
from dotenv import load_dotenv

load_dotenv()

# Supabase設定
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')

# Pinecone設定
PINECONE_API_KEY = os.getenv('PINECONE_API_KEY')

# クライアントを作成
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index("recruitment-matching")

print("1. Pineconeのデータをクリア...")
# ネームスペース内のすべてのデータを削除
index.delete(delete_all=True, namespace="historical-cases")
print("   ✓ Pineconeデータをクリアしました")

print("\n2. Supabaseの同期フラグをリセット...")
# synced_to_pineconeをfalseにリセット
response = supabase.table('client_evaluations').update({
    'synced_to_pinecone': False,
    'sync_error': None,
    'sync_retry_count': 0
}).eq('synced_to_pinecone', True).execute()

print(f"   ✓ {len(response.data)}件のレコードをリセットしました")

# 確認
print("\n3. リセット後の状態確認...")
stats = index.describe_index_stats()
print(f"   Pinecone総ベクトル数: {stats.total_vector_count}")

sync_status = supabase.table('client_evaluations').select('count', count='exact').eq('synced_to_pinecone', False).execute()
print(f"   未同期レコード数: {sync_status.count}")

print("\n✓ リセット完了。再同期の準備ができました。")