"""
Gemini Embedding APIのラッパー
"""

import os
import hashlib
from typing import List, Dict, Optional
import google.generativeai as genai


class GeminiEmbedder:
    """Gemini Embedding APIを使用してテキストをベクトル化"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初期化
        
        Args:
            api_key: Gemini API key. 指定なしの場合は環境変数から取得
        """
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is required")
        
        genai.configure(api_key=self.api_key)
        self.model_name = "models/gemini-embedding-exp-03-07"
        
        # キャッシュ（開発時の無駄なAPI呼び出しを防ぐ）
        self._cache = {}
        
    def embed_text(self, text: str, task_type: str = "retrieval_document") -> List[float]:
        """
        単一のテキストをベクトル化
        
        Args:
            text: ベクトル化するテキスト
            task_type: タスクタイプ。"retrieval_document" or "retrieval_query"
            
        Returns:
            768次元のベクトル
        """
        # キャッシュチェック
        cache_key = self._get_cache_key(text, task_type)
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        try:
            result = genai.embed_content(
                model=self.model_name,
                content=text,
                task_type=task_type
            )
            
            embedding = result['embedding']
            
            # キャッシュに保存
            self._cache[cache_key] = embedding
            
            return embedding
            
        except Exception as e:
            print(f"Embedding error: {e}")
            raise
    
    def embed_batch(self, texts: List[str], task_type: str = "retrieval_document") -> List[List[float]]:
        """
        複数のテキストを一括でベクトル化
        
        Args:
            texts: ベクトル化するテキストのリスト
            task_type: タスクタイプ
            
        Returns:
            ベクトルのリスト
        """
        embeddings = []
        
        # 現在のGemini APIはバッチ処理に制限があるため、個別に処理
        # 将来的にバッチAPIが改善されたら最適化可能
        for text in texts:
            embedding = self.embed_text(text, task_type)
            embeddings.append(embedding)
            
        return embeddings
    
    def embed_case_components(self, case_data: Dict) -> Dict[str, List[float]]:
        """
        評価ケースの各コンポーネントをベクトル化
        
        Args:
            case_data: 評価ケースデータ
            
        Returns:
            各コンポーネントのベクトル
        """
        vectors = {}
        
        # 1. 統合ベクトル（4要素結合）
        combined_text = f"""
ポジション: {case_data.get('position', '')}
求人内容:
{case_data.get('job_description', '')}
求人メモ:
{case_data.get('job_memo', '')}
候補者情報:
{case_data.get('resume', '')}
"""
        vectors['combined'] = self.embed_text(combined_text)
        
        # 2. 求人側ベクトル（ポジション＋求人票＋メモ）
        job_text = f"""
{case_data.get('position', '')}
{case_data.get('job_description', '')}
{case_data.get('job_memo', '')}
"""
        vectors['job_side'] = self.embed_text(job_text)
        
        # 3. 候補者ベクトル
        vectors['candidate'] = self.embed_text(case_data.get('resume', ''))
        
        # 4. 要約ベクトル（存在する場合）
        if 'job_summary' in case_data:
            vectors['job_summary'] = self.embed_text(case_data['job_summary'])
            
        if 'candidate_summary' in case_data:
            vectors['candidate_summary'] = self.embed_text(case_data['candidate_summary'])
            
        if 'evaluation_summary' in case_data:
            summary_text = f"{case_data['position']} → {case_data['evaluation_summary']}"
            vectors['case_summary'] = self.embed_text(summary_text)
        
        return vectors
    
    def embed_search_query(self, query: str) -> List[float]:
        """
        検索クエリ用のベクトル化（retrieval_query タスクタイプを使用）
        
        Args:
            query: 検索クエリ
            
        Returns:
            検索用ベクトル
        """
        return self.embed_text(query, task_type="retrieval_query")
    
    def _get_cache_key(self, text: str, task_type: str) -> str:
        """キャッシュキーの生成"""
        content = f"{task_type}:{text}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def clear_cache(self):
        """キャッシュをクリア"""
        self._cache.clear()
        print("Embedding cache cleared")