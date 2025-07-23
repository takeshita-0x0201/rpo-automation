"""
ベクトルDB同期サービス
client_evaluationsからPineconeへのデータ同期を管理
"""
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import asyncio

from core.utils.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

class VectorSyncService:
    """ベクトルDB同期サービス"""
    
    def __init__(self):
        self.supabase = get_supabase_client()
        self.batch_size = 5  # Gemini無料枠のレート制限に合わせて
        
    async def get_unsynced_evaluations(self, limit: int = 100) -> List[Dict]:
        """
        未同期のclient_evaluationsを取得
        """
        try:
            response = self.supabase.table('client_evaluations')\
                .select('*')\
                .eq('synced_to_pinecone', False)\
                .limit(limit)\
                .execute()
            
            return response.data if response.data else []
        except Exception as e:
            logger.error(f"Error fetching unsynced evaluations: {e}")
            return []
    
    async def collect_related_data(self, evaluation: Dict) -> Optional[Dict]:
        """
        評価に関連するデータを収集
        """
        try:
            candidate_id = evaluation['candidate_id']  # TEXT型（候補者名）
            requirement_id = evaluation['requirement_id']  # TEXT型
            
            # 1. 候補者データを取得
            candidate_data = await self._get_candidate_data(candidate_id)
            if not candidate_data:
                raise ValueError(f"Candidate not found: {candidate_id}")
            
            # 2. 求人要件データを取得
            requirement_data = await self._get_requirement_data(requirement_id)
            if not requirement_data:
                raise ValueError(f"Requirement not found: {requirement_id}")
            
            # 3. AI評価データを取得
            ai_evaluation_data = await self._get_ai_evaluation_data(
                candidate_data['id'],  # UUID
                requirement_data['id']  # UUID
            )
            
            # 4. クライアントデータを取得
            client_data = await self._get_client_data(requirement_data['client_id'])
            
            # データを統合
            return {
                'evaluation': evaluation,
                'candidate': candidate_data,
                'requirement': requirement_data,
                'ai_evaluation': ai_evaluation_data,
                'client': client_data
            }
            
        except Exception as e:
            logger.error(f"Error collecting related data: {e}")
            await self._record_sync_error(evaluation, str(e))
            return None
    
    async def _get_candidate_data(self, candidate_name: str) -> Optional[Dict]:
        """候補者データを取得"""
        try:
            # candidate_idフィールド（実際は名前）で検索
            response = self.supabase.table('candidates')\
                .select('*')\
                .eq('candidate_id', candidate_name)\
                .single()\
                .execute()
            return response.data
        except:
            return None
    
    async def _get_requirement_data(self, requirement_id: str) -> Optional[Dict]:
        """求人要件データを取得"""
        try:
            # requirement_idで検索
            response = self.supabase.table('job_requirements')\
                .select('*')\
                .eq('requirement_id', requirement_id)\
                .single()\
                .execute()
            
            if response.data:
                return response.data
            
            # requirement_idが見つからない場合、UUIDとして検索
            response = self.supabase.table('job_requirements')\
                .select('*')\
                .eq('id', requirement_id)\
                .single()\
                .execute()
            return response.data
        except:
            return None
    
    async def _get_ai_evaluation_data(self, candidate_uuid: str, requirement_uuid: str) -> Optional[Dict]:
        """AI評価データを取得"""
        try:
            response = self.supabase.table('ai_evaluations')\
                .select('*')\
                .eq('candidate_id', candidate_uuid)\
                .eq('requirement_id', requirement_uuid)\
                .single()\
                .execute()
            return response.data
        except:
            return None
    
    async def _get_client_data(self, client_id: str) -> Optional[Dict]:
        """クライアントデータを取得"""
        try:
            response = self.supabase.table('clients')\
                .select('id, name')\
                .eq('id', client_id)\
                .single()\
                .execute()
            return response.data
        except:
            return None
    
    async def _record_sync_error(self, evaluation: Dict, error_message: str):
        """同期エラーを記録"""
        try:
            update_data = {
                'sync_error': error_message,
                'sync_retry_count': (evaluation.get('sync_retry_count', 0) or 0) + 1,
                'updated_at': datetime.now().isoformat()
            }
            
            self.supabase.table('client_evaluations')\
                .update(update_data)\
                .eq('candidate_id', evaluation['candidate_id'])\
                .eq('requirement_id', evaluation['requirement_id'])\
                .execute()
        except Exception as e:
            logger.error(f"Error recording sync error: {e}")
    
    async def mark_as_synced(self, evaluation: Dict):
        """同期完了をマーク"""
        try:
            update_data = {
                'synced_to_pinecone': True,
                'synced_at': datetime.now().isoformat(),
                'sync_error': None,
                'updated_at': datetime.now().isoformat()
            }
            
            self.supabase.table('client_evaluations')\
                .update(update_data)\
                .eq('candidate_id', evaluation['candidate_id'])\
                .eq('requirement_id', evaluation['requirement_id'])\
                .execute()
        except Exception as e:
            logger.error(f"Error marking as synced: {e}")
    
    def prepare_vector_texts(self, data: Dict) -> Dict[str, str]:
        """
        3種類のベクトル用テキストを準備
        """
        evaluation = data['evaluation']
        candidate = data['candidate']
        requirement = data['requirement']
        ai_evaluation = data.get('ai_evaluation', {})
        client = data.get('client', {})
        
        # 1. 求人側ベクトル
        job_side_text = f"""
ポジション: {requirement.get('title', '')}
クライアント: {client.get('name', '')}

求人詳細:
{requirement.get('job_description', '')}

求人メモ:
{requirement.get('memo', '')}
"""
        
        # 2. 候補者ベクトル
        candidate_text = f"""
候補者: {candidate.get('candidate_id', '')}
所属企業: {candidate.get('candidate_company', '')}

レジュメ:
{candidate.get('candidate_resume', '')}

AI評価スコア: {ai_evaluation.get('ai_score', 'N/A')}
推奨度: {ai_evaluation.get('recommendation', 'N/A')}

強み:
{', '.join(ai_evaluation.get('strengths', []))}

懸念点:
{', '.join(ai_evaluation.get('concerns', []))}

クライアント評価: {evaluation.get('client_evaluation', '')}
評価者: {evaluation.get('created_by', '')}
フィードバック: {evaluation.get('client_feedback', '')}
"""
        
        # 3. 統合ベクトル
        combined_text = f"{job_side_text}\n\n{candidate_text}"
        
        return {
            'job_side': job_side_text,
            'candidate': candidate_text,
            'combined': combined_text
        }
    
    def prepare_metadata(self, data: Dict, vector_type: str) -> Dict:
        """
        メタデータを準備
        """
        evaluation = data['evaluation']
        candidate = data['candidate']
        requirement = data['requirement']
        ai_evaluation = data.get('ai_evaluation', {})
        client = data.get('client', {})
        
        # ケースIDの生成
        base_case_id = f"{evaluation['candidate_id']}_{evaluation['requirement_id']}_{evaluation.get('evaluation_date', datetime.now().date())}"
        
        # AI評価とクライアント評価の一致判定
        ai_rec = ai_evaluation.get('recommendation', '')
        client_eval = evaluation.get('client_evaluation', '')
        evaluation_match = self._check_evaluation_match(ai_rec, client_eval)
        
        # 基本メタデータ
        metadata = {
            'case_id': f"{base_case_id}_{vector_type}",
            'vector_type': vector_type,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            
            # 分類情報
            'position': requirement.get('title', ''),
            'client_id': client.get('id', ''),
            'client_name': client.get('name', ''),
            
            # 評価情報
            'ai_recommendation': ai_rec,
            'client_evaluation': client_eval,
            'score': ai_evaluation.get('ai_score', 0),
            'evaluation_match': evaluation_match,
            
            # 検索最適化
            'is_high_quality': ai_evaluation.get('ai_score', 0) >= 80,
            'has_client_feedback': bool(evaluation.get('client_feedback')),
            'is_sharable': True  # 全データ共有可能
        }
        
        return metadata
    
    def _check_evaluation_match(self, ai_rec: str, client_eval: str) -> bool:
        """AI評価とクライアント評価の一致を判定"""
        # 評価のマッピング
        positive_evals = ['A', 'B', '合格', 'Pass', '通過', 'OK']
        negative_evals = ['C', 'D', '不合格', 'Fail', 'NG']
        
        ai_positive = any(eval in ai_rec for eval in positive_evals)
        client_positive = any(eval in client_eval for eval in positive_evals)
        
        return ai_positive == client_positive


# サービスのシングルトンインスタンス
vector_sync_service = VectorSyncService()