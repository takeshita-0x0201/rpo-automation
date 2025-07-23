#!/usr/bin/env python3
"""
Pineconeインデックスの状態を確認するスクリプト
"""
import os
from pinecone import Pinecone

# 環境変数から認証情報を取得
api_key = os.getenv('PINECONE_API_KEY', 'pcsk_4u7L23_9UA9Yco4puyvky5EzxuKm7icECoQQs4wZwHb9zxDkzzhyXPp6SVUUwPUAdEirPz')

# Pineconeクライアントを初期化
pc = Pinecone(api_key=api_key)

# インデックスの設定
index_name = "recruitment-matching"

try:
    # インデックスを取得
    index = pc.Index(index_name)
    
    # インデックス情報を表示
    print(f"インデックス名: {index_name}")
    print(f"ホスト: {index._config.host}")
    
    # インデックスの詳細情報を取得
    stats = index.describe_index_stats()
    print(f"\nインデックス統計:")
    print(f"- 総ベクトル数: {stats.total_vector_count}")
    print(f"- 次元数: {stats.dimension if hasattr(stats, 'dimension') else 'N/A'}")
    print(f"- ネームスペース: {list(stats.namespaces.keys()) if stats.namespaces else 'デフォルトのみ'}")
    
    # テストベクトルを挿入してみる
    print("\nテストベクトルの挿入を試みます...")
    test_vector = {
        "id": "test-vector-1",
        "values": [0.1] * 768,  # 768次元のダミーベクトル
        "metadata": {
            "test": True,
            "description": "Test vector for validation"
        }
    }
    
    # historical-casesネームスペースに挿入
    index.upsert(
        vectors=[test_vector],
        namespace="historical-cases"
    )
    print("✓ テストベクトルの挿入に成功しました")
    
    # 挿入したベクトルを削除
    index.delete(ids=["test-vector-1"], namespace="historical-cases")
    print("✓ テストベクトルを削除しました")
    
except Exception as e:
    print(f"エラーが発生しました: {e}")
    print(f"エラーの詳細: {type(e).__name__}")