#!/usr/bin/env python3
"""
Pineconeに保存されたデータの内容を確認
"""
import os
import json
from pinecone import Pinecone

# 環境変数から認証情報を取得
api_key = os.getenv('PINECONE_API_KEY', 'pcsk_4u7L23_9UA9Yco4puyvky5EzxuKm7icECoQQs4wZwHb9zxDkzzhyXPp6SVUUwPUAdEirPz')

# Pineconeクライアントを初期化
pc = Pinecone(api_key=api_key)
index = pc.Index("recruitment-matching")

# データをフェッチ
print("Pineconeからデータを取得中...\n")

# ランダムにベクトルをフェッチ
stats = index.describe_index_stats()
print(f"総ベクトル数: {stats.total_vector_count}")
print(f"ネームスペース: {list(stats.namespaces.keys())}\n")

# サンプルクエリでデータ構造を確認
sample_vector = [0.1] * 768
results = index.query(
    vector=sample_vector,
    top_k=3,
    include_metadata=True,
    namespace="historical-cases"
)

print("保存されているデータのサンプル:")
print("-" * 80)

for i, match in enumerate(results.matches):
    print(f"\n【サンプル {i+1}】")
    print(f"ID: {match.id}")
    print(f"スコア: {match.score}")
    print(f"\nメタデータ:")
    for key, value in match.metadata.items():
        print(f"  - {key}: {value}")
    print("-" * 40)

# 特定のベクトルタイプごとのカウント
print("\n\nベクトルタイプ別の統計:")
vector_types = {}
for ns_name, ns_stats in stats.namespaces.items():
    print(f"\nネームスペース: {ns_name}")
    # 実際のデータをクエリして統計を取る
    sample_results = index.query(
        vector=sample_vector,
        top_k=100,
        include_metadata=True,
        namespace=ns_name
    )
    
    for match in sample_results.matches:
        vtype = match.metadata.get('vector_type', 'unknown')
        if vtype not in vector_types:
            vector_types[vtype] = 0
        vector_types[vtype] += 1

for vtype, count in vector_types.items():
    print(f"  - {vtype}: {count}件")

# メタデータフィールドの確認
print("\n\n利用可能なメタデータフィールド:")
if results.matches:
    sample_metadata = results.matches[0].metadata
    for key in sample_metadata.keys():
        print(f"  - {key}")

# フィルタリングのテスト
print("\n\nフィルタリングテスト:")
print("1. 高スコア（is_high_quality=true）の案件:")
filtered_results = index.query(
    vector=sample_vector,
    top_k=5,
    include_metadata=True,
    namespace="historical-cases",
    filter={"is_high_quality": True}
)
print(f"   見つかった件数: {len(filtered_results.matches)}")

print("\n2. 特定のベクトルタイプ（job_side）:")
filtered_results = index.query(
    vector=sample_vector,
    top_k=5,
    include_metadata=True,
    namespace="historical-cases",
    filter={"vector_type": "job_side"}
)
print(f"   見つかった件数: {len(filtered_results.matches)}")

print("\n3. 評価が一致している案件（evaluation_match=true）:")
filtered_results = index.query(
    vector=sample_vector,
    top_k=5,
    include_metadata=True,
    namespace="historical-cases",
    filter={"evaluation_match": True}
)
print(f"   見つかった件数: {len(filtered_results.matches)}")