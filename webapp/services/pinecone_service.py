"""
Pineconeサービス
ベクトルデータベースへの保存と検索
"""
import os
import logging
from typing import List, Dict, Optional, Tuple
from pinecone import Pinecone, ServerlessSpec
import asyncio

logger = logging.getLogger(__name__)

class PineconeService:
    """Pineconeサービス"""
    
    # インデックス設定
    INDEX_NAME = "recruitment-matching"
    NAMESPACE = "historical-cases"
    DIMENSION = 768  # Gemini embedding-001の次元数
    METRIC = "cosine"
    
    # バッチサイズ
    UPSERT_BATCH_SIZE = 100
    
    def __init__(self):
        # Pinecone APIキーの取得
        api_key = os.getenv('PINECONE_API_KEY')
        if not api_key:
            raise ValueError("PINECONE_API_KEY is not set")
        
        # Pineconeクライアントの初期化
        self.pc = Pinecone(api_key=api_key)
        
        # インデックスの初期化
        self._initialize_index()
    
    def _initialize_index(self):
        """インデックスの初期化（存在しない場合は作成）"""
        try:
            # 既存インデックスのチェック
            indexes = self.pc.list_indexes()
            index_names = [idx.name for idx in indexes]
            
            if self.INDEX_NAME not in index_names:
                logger.info(f"Creating new index: {self.INDEX_NAME}")
                
                # 新規インデックスの作成
                self.pc.create_index(
                    name=self.INDEX_NAME,
                    dimension=self.DIMENSION,
                    metric=self.METRIC,
                    spec=ServerlessSpec(
                        cloud='aws',
                        region='us-east-1'
                    )
                )
                
                # インデックスの準備を待つ
                import time
                time.sleep(10)
            
            # インデックスへの接続
            self.index = self.pc.Index(self.INDEX_NAME)
            logger.info(f"Connected to index: {self.INDEX_NAME}")
            
        except Exception as e:
            logger.error(f"Error initializing Pinecone index: {e}")
            raise
    
    async def upsert_vectors(self, vectors: List[Tuple[str, List[float], Dict]]) -> bool:
        """
        ベクトルをPineconeに保存
        
        Args:
            vectors: (id, vector, metadata)のタプルのリスト
            
        Returns:
            成功した場合True
        """
        try:
            # バッチ処理
            for i in range(0, len(vectors), self.UPSERT_BATCH_SIZE):
                batch = vectors[i:i + self.UPSERT_BATCH_SIZE]
                
                # Pinecone形式に変換
                upsert_data = []
                for vector_id, vector, metadata in batch:
                    upsert_data.append({
                        'id': vector_id,
                        'values': vector,
                        'metadata': metadata
                    })
                
                # アップサート実行
                self.index.upsert(
                    vectors=upsert_data,
                    namespace=self.NAMESPACE
                )
                
                logger.info(f"Upserted {len(batch)} vectors to Pinecone")
                
                # 小さな待機時間
                await asyncio.sleep(0.1)
            
            return True
            
        except Exception as e:
            logger.error(f"Error upserting vectors: {e}")
            return False
    
    async def delete_vectors(self, vector_ids: List[str]) -> bool:
        """
        ベクトルをPineconeから削除
        
        Args:
            vector_ids: 削除するベクトルIDのリスト
            
        Returns:
            成功した場合True
        """
        try:
            self.index.delete(
                ids=vector_ids,
                namespace=self.NAMESPACE
            )
            logger.info(f"Deleted {len(vector_ids)} vectors from Pinecone")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting vectors: {e}")
            return False
    
    async def query_similar(
        self, 
        query_vector: List[float], 
        top_k: int = 10,
        filter_dict: Optional[Dict] = None,
        include_metadata: bool = True
    ) -> List[Dict]:
        """
        類似ベクトルを検索
        
        Args:
            query_vector: クエリベクトル
            top_k: 返す結果の数
            filter_dict: メタデータフィルタ
            include_metadata: メタデータを含めるか
            
        Returns:
            類似ベクトルのリスト
        """
        try:
            results = self.index.query(
                vector=query_vector,
                top_k=top_k,
                filter=filter_dict,
                include_metadata=include_metadata,
                namespace=self.NAMESPACE
            )
            
            return results.matches
            
        except Exception as e:
            logger.error(f"Error querying vectors: {e}")
            return []
    
    def get_index_stats(self) -> Dict:
        """インデックスの統計情報を取得"""
        try:
            stats = self.index.describe_index_stats()
            return {
                "total_vectors": stats.total_vector_count,
                "dimension": stats.dimension,
                "namespace_stats": stats.namespaces,
                "index_fullness": stats.index_fullness
            }
        except Exception as e:
            logger.error(f"Error getting index stats: {e}")
            return {}


# サービスのシングルトンインスタンス
pinecone_service = PineconeService()