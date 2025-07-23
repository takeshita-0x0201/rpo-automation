#!/usr/bin/env python3
"""
Pineconeインデックスを作成するスクリプト
"""
import os
from pinecone import Pinecone, ServerlessSpec

# 環境変数から認証情報を取得
api_key = os.getenv('PINECONE_API_KEY', 'pcsk_4u7L23_9UA9Yco4puyvky5EzxuKm7icECoQQs4wZwHb9zxDkzzhyXPp6SVUUwPUAdEirPz')

# Pineconeクライアントを初期化
pc = Pinecone(api_key=api_key)

# インデックスの設定
index_name = "recruitment-matching"
dimension = 768  # Gemini Embeddingの次元数

# 既存のインデックスを確認
existing_indexes = pc.list_indexes()
print(f"既存のインデックス: {[idx.name for idx in existing_indexes]}")

if index_name not in [idx.name for idx in existing_indexes]:
    print(f"インデックス '{index_name}' を作成中...")
    
    # Serverless環境でインデックスを作成
    # 無料プランでは通常 'us-east-1' リージョンを使用
    pc.create_index(
        name=index_name,
        dimension=dimension,
        metric='cosine',  # コサイン類似度
        spec=ServerlessSpec(
            cloud='aws',
            region='us-east-1'  # 無料プランの標準リージョン
        )
    )
    
    print(f"インデックス '{index_name}' を作成しました")
else:
    print(f"インデックス '{index_name}' は既に存在します")

# インデックス情報を取得
index = pc.Index(index_name)
stats = index.describe_index_stats()

print(f"\nインデックス情報:")
print(f"- 名前: {index_name}")
print(f"- 次元数: {dimension}")
print(f"- メトリック: cosine")
print(f"- ホスト: {index._config.host}")
print(f"- 総ベクトル数: {stats.total_vector_count}")

print(f"\n以下のコマンドでSupabaseにホストを設定してください:")
print(f'supabase secrets set PINECONE_INDEX_HOST="{index._config.host}"')