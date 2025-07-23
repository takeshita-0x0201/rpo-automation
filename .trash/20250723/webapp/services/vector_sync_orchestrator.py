"""
ベクトル同期オーケストレーター
全体の同期処理を管理
"""
import logging
import asyncio
from typing import List, Dict, Optional
from datetime import datetime

from .vector_sync_service import vector_sync_service
from .embedding_service import embedding_service
from .pinecone_service import pinecone_service

logger = logging.getLogger(__name__)

class VectorSyncOrchestrator:
    """ベクトル同期オーケストレーター"""
    
    # 処理設定
    MAX_RETRIES = 3
    CANDIDATES_PER_BATCH = 5  # Gemini無料枠に合わせて
    
    def __init__(self):
        self.vector_sync = vector_sync_service
        self.embedding = embedding_service
        self.pinecone = pinecone_service
    
    async def sync_batch(self, limit: int = None) -> Dict:
        """
        バッチ同期処理のメインエントリーポイント
        
        Returns:
            処理結果のサマリー
        """
        if limit is None:
            limit = self.CANDIDATES_PER_BATCH
        
        start_time = datetime.now()
        results = {
            'processed': 0,
            'success': 0,
            'failed': 0,
            'errors': []
        }
        
        try:
            # 1. 未同期の評価を取得
            evaluations = await self.vector_sync.get_unsynced_evaluations(limit)
            logger.info(f"Found {len(evaluations)} unsynced evaluations")
            
            if not evaluations:
                return results
            
            # 2. 各評価を処理
            for evaluation in evaluations:
                try:
                    success = await self._process_single_evaluation(evaluation)
                    
                    if success:
                        results['success'] += 1
                    else:
                        results['failed'] += 1
                        
                    results['processed'] += 1
                    
                except Exception as e:
                    logger.error(f"Error processing evaluation: {e}")
                    results['failed'] += 1
                    results['errors'].append({
                        'candidate_id': evaluation.get('candidate_id'),
                        'error': str(e)
                    })
            
            # 3. 処理時間を記録
            duration = (datetime.now() - start_time).total_seconds()
            results['duration_seconds'] = duration
            
            # 4. 残りのクォータを記録
            results['embedding_quota'] = self.embedding.get_remaining_quota()
            
            logger.info(f"Sync batch completed: {results}")
            return results
            
        except Exception as e:
            logger.error(f"Fatal error in sync batch: {e}")
            results['errors'].append({'error': f'Fatal: {str(e)}'})
            return results
    
    async def _process_single_evaluation(self, evaluation: Dict) -> bool:
        """
        単一評価の処理
        
        Returns:
            成功した場合True
        """
        candidate_id = evaluation.get('candidate_id')
        requirement_id = evaluation.get('requirement_id')
        
        logger.info(f"Processing evaluation: {candidate_id} - {requirement_id}")
        
        try:
            # 1. 関連データを収集
            data = await self.vector_sync.collect_related_data(evaluation)
            if not data:
                logger.error(f"Failed to collect data for {candidate_id}")
                return False
            
            # 2. 必須フィールドの検証
            validation_error = self._validate_required_fields(data)
            if validation_error:
                await self.vector_sync._record_sync_error(evaluation, validation_error)
                return False
            
            # 3. 既存ベクトルの削除（上書き更新）
            await self._delete_existing_vectors(evaluation)
            
            # 4. ベクトルテキストを準備
            vector_texts = self.vector_sync.prepare_vector_texts(data)
            
            # 5. エンベディングを生成
            embeddings = await self._generate_embeddings_with_retry(vector_texts)
            if not embeddings:
                await self.vector_sync._record_sync_error(evaluation, "Failed to generate embeddings")
                return False
            
            # 6. Pineconeに保存
            vectors_to_save = []
            for vector_type, embedding in embeddings.items():
                if embedding:
                    metadata = self.vector_sync.prepare_metadata(data, vector_type)
                    vector_id = metadata['case_id']
                    vectors_to_save.append((vector_id, embedding, metadata))
            
            if vectors_to_save:
                success = await self.pinecone.upsert_vectors(vectors_to_save)
                if success:
                    # 7. 同期完了をマーク
                    await self.vector_sync.mark_as_synced(evaluation)
                    logger.info(f"Successfully synced {candidate_id} - {requirement_id}")
                    return True
                else:
                    await self.vector_sync._record_sync_error(evaluation, "Failed to save to Pinecone")
                    return False
            
            return False
            
        except Exception as e:
            logger.error(f"Error processing evaluation {candidate_id}: {e}")
            await self.vector_sync._record_sync_error(evaluation, str(e))
            return False
    
    def _validate_required_fields(self, data: Dict) -> Optional[str]:
        """必須フィールドの検証"""
        errors = []
        
        # 必須データの存在確認
        if not data.get('candidate'):
            errors.append("候補者データが見つかりません")
        elif not data['candidate'].get('candidate_resume'):
            errors.append("レジュメが存在しません")
        
        if not data.get('requirement'):
            errors.append("求人要件データが見つかりません")
        else:
            if not data['requirement'].get('job_description'):
                errors.append("求人票が存在しません")
            if not data['requirement'].get('memo'):
                errors.append("求人メモが存在しません")
        
        if not data.get('evaluation', {}).get('client_evaluation'):
            errors.append("クライアント評価が存在しません")
        
        return ", ".join(errors) if errors else None
    
    async def _delete_existing_vectors(self, evaluation: Dict):
        """既存ベクトルの削除（上書き更新のため）"""
        try:
            base_case_id = f"{evaluation['candidate_id']}_{evaluation['requirement_id']}_{evaluation.get('evaluation_date', datetime.now().date())}"
            vector_ids = [
                f"{base_case_id}_combined",
                f"{base_case_id}_job_side",
                f"{base_case_id}_candidate"
            ]
            
            await self.pinecone.delete_vectors(vector_ids)
            
        except Exception as e:
            logger.warning(f"Error deleting existing vectors: {e}")
    
    async def _generate_embeddings_with_retry(self, vector_texts: Dict[str, str]) -> Dict[str, Optional[List[float]]]:
        """リトライ付きエンベディング生成"""
        embeddings = {}
        
        for vector_type, text in vector_texts.items():
            embedding = None
            
            for attempt in range(self.MAX_RETRIES):
                try:
                    embedding = await self.embedding.generate_embedding(
                        text=text,
                        title=f"{vector_type}_vector"
                    )
                    
                    if embedding:
                        break
                        
                except Exception as e:
                    logger.warning(f"Embedding attempt {attempt + 1} failed: {e}")
                    if attempt < self.MAX_RETRIES - 1:
                        await asyncio.sleep(2 ** attempt)  # 指数バックオフ
            
            embeddings[vector_type] = embedding
        
        return embeddings
    
    async def run_continuous_sync(self, interval_minutes: int = 60):
        """
        継続的な同期処理
        
        Args:
            interval_minutes: 実行間隔（分）
        """
        logger.info(f"Starting continuous sync with {interval_minutes} minute interval")
        
        while True:
            try:
                # バッチ処理を実行
                results = await self.sync_batch()
                
                # 次回実行まで待機
                await asyncio.sleep(interval_minutes * 60)
                
            except Exception as e:
                logger.error(f"Error in continuous sync: {e}")
                # エラー時も継続
                await asyncio.sleep(60)


# オーケストレーターのシングルトンインスタンス
vector_sync_orchestrator = VectorSyncOrchestrator()