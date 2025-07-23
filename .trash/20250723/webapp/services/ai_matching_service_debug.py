"""
AIマッチングシステムとの統合サービス（デバッグ版）
既存のCLIツールをWebアプリから呼び出す
"""
import os
import sys
import json
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid
from dotenv import load_dotenv

# .envファイルを読み込む
load_dotenv()

# ai_matching_systemをインポートパスに追加
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
ai_matching_path = os.path.join(project_root, "ai_matching_system")
sys.path.append(ai_matching_path)

# AIマッチングシステムのインポート
try:
    from ai_matching.nodes.orchestrator import SeparatedDeepResearchMatcher
except ImportError as e:
    print(f"Warning: Could not import AI matching system: {e}")
    SeparatedDeepResearchMatcher = None

from core.utils.supabase_client import get_supabase_client

class AIMatchingService:
    """AIマッチングシステムとの統合サービス"""
    
    def __init__(self):
        self.supabase = get_supabase_client()
        self.matcher = None
        self._initialize_matcher()
    
    def _initialize_matcher(self):
        """マッチャーの初期化"""
        if SeparatedDeepResearchMatcher is None:
            print("Warning: AI matching system not available")
            self.matcher = None
            return
            
        try:
            self.matcher = SeparatedDeepResearchMatcher(
                gemini_api_key=os.getenv('GEMINI_API_KEY'),
                tavily_api_key=os.getenv('TAVILY_API_KEY'),
                pinecone_api_key=os.getenv('PINECONE_API_KEY')
            )
            print(f"DEBUG: Matcher initialized successfully: {self.matcher}")
        except Exception as e:
            print(f"Failed to initialize matcher: {e}")
            self.matcher = None
            # API キーが設定されていない場合でも続行
    
    async def process_job(self, job_id: str):
        """ジョブを処理"""
        print(f"\nDEBUG: Starting process_job for {job_id}")
        print(f"DEBUG: Current matcher status: {self.matcher}")
        
        try:
            # ジョブ情報を取得
            job = await self._get_job_details(job_id)
            if not job:
                raise Exception(f"Job {job_id} not found")
            
            # ジョブステータスを更新
            await self._update_job_status(job_id, 'running', 0)
            
            # 要件情報を取得
            requirement = await self._get_requirement(job['requirement_id'])
            if not requirement:
                raise Exception(f"Requirement {job['requirement_id']} not found")
            
            # 候補者を取得（スクレイピング結果から）
            candidates = await self._get_candidates_for_job(job)
            
            print(f"Job {job_id}: Found {len(candidates)} candidates")
            print(f"Job details: client_id={job.get('client_id')}, requirement_id={job.get('requirement_id')}")
            
            if not candidates:
                print(f"No candidates found for job {job_id}, completing job")
                await self._update_job_status(job_id, 'completed', 100)
                return
            
            total_candidates = len(candidates)
            processed = 0
            
            # 各候補者を評価
            for candidate in candidates:
                try:
                    # 進捗更新
                    progress = int((processed / total_candidates) * 100)
                    await self._update_job_status(job_id, 'running', progress)
                    
                    # Supabaseから取得したデータを直接使用
                    resume_text = candidate.get('candidate_resume', '')
                    job_desc_text = self._format_job_description(requirement)
                    job_memo_text = self._format_job_memo(requirement)
                    
                    print(f"\nDEBUG: Processing candidate {candidate.get('id')}")
                    print(f"DEBUG: Resume length: {len(resume_text)}")
                    print(f"DEBUG: Matcher status: {self.matcher}")
                    print(f"DEBUG: Has match_candidate_direct: {hasattr(self.matcher, 'match_candidate_direct') if self.matcher else 'N/A'}")
                    
                    # AIマッチング実行
                    if self.matcher and hasattr(self.matcher, 'match_candidate_direct'):
                        print(f"DEBUG: Using actual AI matching")
                        # 直接テキストを渡す
                        result = await asyncio.to_thread(
                            self.matcher.match_candidate_direct,
                            resume_text=resume_text,
                            job_description_text=job_desc_text,
                            job_memo_text=job_memo_text,
                            max_cycles=3
                        )
                        print(f"DEBUG: AI matching result - Score: {result.get('final_score')}, Rec: {result.get('final_judgment', {}).get('recommendation')}")
                    else:
                        print(f"DEBUG: Using dummy result (matcher={self.matcher})")
                        # マッチャーが初期化されていない場合のダミー結果
                        result = self._generate_dummy_result()
                        print(f"DEBUG: Dummy result - Score: {result.get('final_score')}, Rec: {result.get('final_judgment', {}).get('recommendation')}")
                    
                    # 結果を保存
                    await self._save_evaluation_result(job_id, candidate, result)
                    
                    processed += 1
                    
                except Exception as e:
                    print(f"Error processing candidate {candidate.get('id')}: {e}")
                    import traceback
                    traceback.print_exc()
                    # エラーでも続行
                    processed += 1
            
            # ジョブ完了
            await self._update_job_status(job_id, 'completed', 100)
            
        except Exception as e:
            print(f"Error processing job {job_id}: {e}")
            import traceback
            traceback.print_exc()
            await self._update_job_status(job_id, 'failed', error_message=str(e))
    
    async def _get_job_details(self, job_id: str) -> Optional[Dict]:
        """ジョブ詳細を取得"""
        response = self.supabase.table('jobs').select('*').eq('id', job_id).single().execute()
        return response.data
    
    async def _get_requirement(self, requirement_id: str) -> Optional[Dict]:
        """要件情報を取得"""
        response = self.supabase.table('job_requirements').select('*, client:clients(*)').eq('id', requirement_id).single().execute()
        return response.data
    
    async def _get_candidates_for_job(self, job: Dict) -> List[Dict]:
        """ジョブに関連する候補者を取得"""
        # job_parameters から検索条件を取得
        params = job.get('parameters', {})
        
        print(f"Getting candidates for job: {job.get('id')}")
        print(f"  client_id: {job.get('client_id')}")
        print(f"  requirement_id: {job.get('requirement_id')}")
        
        # 候補者を取得（最新のスクレイピング結果から）
        query = self.supabase.table('candidates').select('*')
        
        # 要件IDでフィルタ
        if job.get('requirement_id'):
            query = query.eq('requirement_id', job['requirement_id'])
            print(f"  Filtering by requirement_id: {job['requirement_id']}")
        
        # クライアントIDでフィルタ
        if job.get('client_id'):
            query = query.eq('client_id', job['client_id'])
            print(f"  Filtering by client_id: {job['client_id']}")
        
        # 最新の100件まで
        query = query.order('scraped_at', desc=True).limit(100)
        
        response = query.execute()
        candidates = response.data or []
        
        print(f"  Found {len(candidates)} candidates")
        if candidates:
            print(f"  First candidate: {candidates[0].get('candidate_id')} - {candidates[0].get('candidate_company')}")
        
        return candidates
    
    
    def _format_job_description(self, requirement: Dict) -> str:
        """要件をジョブ記述文形式に変換"""
        sections = []
        
        # 基本情報
        sections.append(f"【ポジション】{requirement.get('title', '')}")
        
        if requirement.get('client', {}).get('name'):
            sections.append(f"【企業名】{requirement['client']['name']}")
        
        # 構造化データから情報を抽出
        structured = requirement.get('structured_data', {})
        
        if structured.get('position_details'):
            sections.append(f"【ポジション詳細】\n{structured['position_details']}")
        
        if structured.get('required_experience'):
            sections.append(f"【必須経験】\n{structured['required_experience']}")
        
        if structured.get('preferred_experience'):
            sections.append(f"【歓迎経験】\n{structured['preferred_experience']}")
        
        if structured.get('job_description'):
            sections.append(f"【職務内容】\n{structured['job_description']}")
        
        # 従来のdescriptionフィールド
        if requirement.get('description'):
            sections.append(f"【詳細説明】\n{requirement['description']}")
        
        return '\n\n'.join(sections)
    
    def _format_job_memo(self, requirement: Dict) -> str:
        """要件のメモ情報を抽出"""
        sections = []
        
        structured = requirement.get('structured_data', {})
        
        # メモ関連の情報
        if structured.get('job_memo'):
            sections.append(structured['job_memo'])
        
        if structured.get('salary_range'):
            sections.append(f"【想定年収】{structured['salary_range']}")
        
        if structured.get('selection_process'):
            sections.append(f"【選考プロセス】{structured['selection_process']}")
        
        if structured.get('team_structure'):
            sections.append(f"【チーム構成】{structured['team_structure']}")
        
        if structured.get('company_culture'):
            sections.append(f"【企業文化】{structured['company_culture']}")
        
        return '\n\n'.join(sections)
    
    async def _save_evaluation_result(self, job_id: str, candidate: Dict, result: Dict):
        """評価結果を保存"""
        # 候補者から requirement_id を取得
        requirement_id = candidate.get('requirement_id')
        
        evaluation_data = {
            'id': str(uuid.uuid4()),
            'search_id': job_id,  # jobs.idを参照
            'candidate_id': candidate['id'],
            'requirement_id': requirement_id,  # requirement_idを追加
            'ai_score': result.get('final_score', 0),
            'match_score': result.get('final_score', 0),
            'recommendation': result.get('final_judgment', {}).get('recommendation', 'D'),
            'confidence': self._convert_confidence(result.get('final_confidence', 'Low')),
            'evaluation_result': {
                'strengths': result.get('final_judgment', {}).get('strengths', []),
                'concerns': result.get('final_judgment', {}).get('concerns', []),
                'interview_points': result.get('final_judgment', {}).get('interview_points', []),
                'overall_assessment': result.get('final_judgment', {}).get('overall_assessment', ''),
                'total_cycles': result.get('total_cycles', 0),
                'total_searches': result.get('total_searches', 0)
            },
            'evaluated_at': datetime.utcnow().isoformat()
        }
        
        print(f"Saving evaluation for candidate {candidate['id']}, requirement_id: {requirement_id}")
        
        try:
            self.supabase.table('ai_evaluations').upsert(evaluation_data).execute()
            print(f"✓ Evaluation saved successfully for candidate {candidate['id']}")
        except Exception as e:
            print(f"✗ Error saving evaluation for candidate {candidate['id']}: {e}")
            raise
    
    async def _update_job_status(self, job_id: str, status: str, progress: int = 0, error_message: str = None):
        """ジョブステータスを更新"""
        update_data = {
            'status': status,
            'progress': progress,
            'updated_at': datetime.utcnow().isoformat()
        }
        
        if error_message:
            update_data['error_message'] = error_message
        
        if status == 'running' and progress == 0:
            update_data['started_at'] = datetime.utcnow().isoformat()
        elif status in ['completed', 'failed']:
            update_data['completed_at'] = datetime.utcnow().isoformat()
        
        self.supabase.table('jobs').update(update_data).eq('id', job_id).execute()
        
        # ステータス履歴も更新
        history_data = {
            'job_id': job_id,
            'status': status,
            'message': error_message or f'Status changed to {status}',
            'created_at': datetime.utcnow().isoformat()
        }
        self.supabase.table('job_status_history').insert(history_data).execute()
    
    def _convert_confidence(self, confidence: str) -> str:
        """英語のconfidenceを日本語に変換"""
        conversion = {
            'Low': '低',
            'Medium': '中', 
            'High': '高'
        }
        return conversion.get(confidence, confidence)
    
    def _generate_dummy_result(self) -> Dict:
        """APIキーがない場合のダミー結果"""
        return {
            'final_score': 75,
            'final_confidence': 'Medium',
            'final_judgment': {
                'recommendation': 'B',
                'strengths': [
                    '豊富な実務経験',
                    '必要な技術スキルを保有',
                    'チームマネジメント経験'
                ],
                'concerns': [
                    '業界経験が不足',
                    '転職回数がやや多い'
                ],
                'interview_points': [
                    'チームビルディングの具体的な経験',
                    '技術選定の判断基準',
                    '長期的なキャリアビジョン'
                ],
                'overall_assessment': '技術力と経験は十分ですが、業界特有の知識については面接で確認が必要です。'
            },
            'total_cycles': 1,
            'total_searches': 0
        }

# シングルトンインスタンス
ai_matching_service = AIMatchingService()