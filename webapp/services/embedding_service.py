"""
Gemini Embeddingサービス
テキストのベクトル化処理
"""
import os
import logging
import asyncio
from typing import List, Optional
import google.generativeai as genai
from datetime import datetime

logger = logging.getLogger(__name__)

class GeminiEmbeddingService:
    """Gemini Embeddingサービス"""
    
    # Gemini API制限（無料枠）
    GEMINI_RPM = 15  # 分あたりリクエスト数
    GEMINI_DAILY_LIMIT = 1500  # 1日あたりリクエスト数
    GEMINI_DELAY = 4.0  # リクエスト間の待機時間（60秒/15リクエスト）
    
    # エンベディングモデル
    EMBEDDING_MODEL = "models/embedding-001"
    EMBEDDING_DIMENSION = 768
    
    def __init__(self):
        # Gemini APIの設定
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set")
        
        genai.configure(api_key=api_key)
        self.last_request_time = None
        self.daily_request_count = 0
        self.daily_reset_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    async def generate_embedding(self, text: str, title: str = "Embedding") -> Optional[List[float]]:
        """
        単一テキストのエンベディングを生成
        
        Args:
            text: エンベディング対象のテキスト
            title: タスクのタイトル（ログ用）
            
        Returns:
            エンベディングベクトル（768次元）
        """
        try:
            # レート制限のチェック
            await self._check_rate_limit()
            
            # テキストの前処理
            processed_text = self._preprocess_text(text)
            
            # エンベディングの生成
            result = genai.embed_content(
                model=self.EMBEDDING_MODEL,
                content=processed_text,
                task_type="retrieval_document",
                title=title
            )
            
            # リクエストカウントを更新
            self._update_request_count()
            
            return result['embedding']
            
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None
    
    async def generate_embeddings_batch(self, texts: List[str], titles: List[str]) -> List[Optional[List[float]]]:
        """
        複数テキストのエンベディングを生成（順次処理）
        
        Args:
            texts: エンベディング対象のテキストリスト
            titles: タスクのタイトルリスト
            
        Returns:
            エンベディングベクトルのリスト
        """
        embeddings = []
        
        for text, title in zip(texts, titles):
            embedding = await self.generate_embedding(text, title)
            embeddings.append(embedding)
        
        return embeddings
    
    def _preprocess_text(self, text: str) -> str:
        """
        テキストの前処理
        - 空白の正規化
        - 長さ制限（Geminiの制限に合わせる）
        """
        # 空白の正規化
        text = ' '.join(text.split())
        
        # 長さ制限（約2048トークン相当の文字数）
        max_chars = 8000
        if len(text) > max_chars:
            text = text[:max_chars] + "..."
            logger.warning(f"Text truncated to {max_chars} characters")
        
        return text
    
    async def _check_rate_limit(self):
        """レート制限のチェックと待機"""
        now = datetime.now()
        
        # 日次リセットのチェック
        if now.date() > self.daily_reset_time.date():
            self.daily_request_count = 0
            self.daily_reset_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # 日次制限のチェック
        if self.daily_request_count >= self.GEMINI_DAILY_LIMIT:
            raise Exception(f"Daily limit reached: {self.GEMINI_DAILY_LIMIT} requests")
        
        # 分間制限のための待機
        if self.last_request_time:
            elapsed = (now - self.last_request_time).total_seconds()
            if elapsed < self.GEMINI_DELAY:
                wait_time = self.GEMINI_DELAY - elapsed
                logger.debug(f"Rate limiting: waiting {wait_time:.2f} seconds")
                await asyncio.sleep(wait_time)
        
        self.last_request_time = datetime.now()
    
    def _update_request_count(self):
        """リクエストカウントを更新"""
        self.daily_request_count += 1
        logger.debug(f"Daily request count: {self.daily_request_count}/{self.GEMINI_DAILY_LIMIT}")
    
    def get_remaining_quota(self) -> dict:
        """残りのクォータを取得"""
        return {
            "daily_remaining": self.GEMINI_DAILY_LIMIT - self.daily_request_count,
            "daily_limit": self.GEMINI_DAILY_LIMIT,
            "rpm_limit": self.GEMINI_RPM
        }


# サービスのシングルトンインスタンス
embedding_service = GeminiEmbeddingService()