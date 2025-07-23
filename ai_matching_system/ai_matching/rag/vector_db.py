"""Vector Database for Recruitment RAG System

ChromaDBからPineconeへの移行
このファイルは後方互換性のために残されています。
新規実装はpinecone_vector_db.pyを使用してください。
"""

import warnings
from .pinecone_vector_db import UnifiedPineconeDB

# 非推奨警告
warnings.warn(
    "vector_db.RecruitmentVectorDB is deprecated. "
    "Please use pinecone_vector_db.UnifiedPineconeDB instead.",
    DeprecationWarning,
    stacklevel=2
)

# 後方互換性のためのエイリアス
RecruitmentVectorDB = UnifiedPineconeDB