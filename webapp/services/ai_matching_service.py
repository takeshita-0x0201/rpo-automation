"""
AIマッチングシステムとの統合サービス
既存のCLIツールをWebアプリから呼び出す
"""
import os
import sys
import json
import asyncio
from typing import Dict, List, Any, Optional, Tuple
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
    from ai_matching.utils.resume_parser import ResumeParser
except ImportError as e:
    print(f"Warning: Could not import AI matching system: {e}")
    SeparatedDeepResearchMatcher = None
    ResumeParser = None

from core.utils.supabase_client import get_supabase_client

class AIMatchingService:
    """AIマッチングシステムとの統合サービス"""
    
    def __init__(self):
        self.supabase = get_supabase_client()
        self.matcher = None
        self.resume_parser = None
        self._initialize_matcher()
        self._initialize_resume_parser()
    
    def _initialize_matcher(self):
        """マッチャーの初期化"""
        print(f"[AI Matching] Initializing matcher...")
        print(f"[AI Matching] SeparatedDeepResearchMatcher available: {SeparatedDeepResearchMatcher is not None}")
        
        if SeparatedDeepResearchMatcher is None:
            print("[AI Matching] Warning: AI matching system not available (import failed)")
            self.matcher = None
            return
            
        try:
            # APIキーの状態を確認
            gemini_key = os.getenv('GEMINI_API_KEY')
            tavily_key = os.getenv('TAVILY_API_KEY')
            pinecone_key = os.getenv('PINECONE_API_KEY')
            
            print(f"[AI Matching] API Keys - Gemini: {'Set' if gemini_key else 'Not set'}, Tavily: {'Set' if tavily_key else 'Not set'}, Pinecone: {'Set' if pinecone_key else 'Not set'}")
            
            self.matcher = SeparatedDeepResearchMatcher(
                gemini_api_key=gemini_key,
                tavily_api_key=tavily_key,
                pinecone_api_key=pinecone_key
            )
            print(f"[AI Matching] Matcher initialized successfully: {type(self.matcher)}")
        except Exception as e:
            print(f"[AI Matching] Failed to initialize matcher: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            self.matcher = None
            # API キーが設定されていない場合でも続行
    
    def _initialize_resume_parser(self):
        """レジュメパーサーの初期化"""
        print(f"[AI Matching] Initializing resume parser...")
        print(f"[AI Matching] ResumeParser available: {ResumeParser is not None}")
        
        if ResumeParser is None:
            print("[AI Matching] Warning: Resume parser not available (import failed)")
            self.resume_parser = None
            return
            
        try:
            # APIキーの状態を確認
            gemini_key = os.getenv('GEMINI_API_KEY')
            
            print(f"[AI Matching] Resume Parser - Gemini API Key: {'Set' if gemini_key else 'Not set'}")
            
            self.resume_parser = ResumeParser(api_key=gemini_key)
            print(f"[AI Matching] Resume parser initialized successfully")
        except Exception as e:
            print(f"[AI Matching] Failed to initialize resume parser: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            self.resume_parser = None
    
    async def process_job(self, job_id: str):
        """ジョブを処理"""
        try:
            # ジョブ情報を取得
            job = await self._get_job_details(job_id)
            if not job:
                raise Exception(f"Job {job_id} not found")
            
            # ジョブステータスを更新（既にrunningの場合はスキップ）
            job_status = job.get('status')
            if job_status != 'running':
                await self._update_job_status(job_id, 'running', 0)
            
            # 要件情報を取得
            requirement = await self._get_requirement(job['requirement_id'])
            if not requirement:
                raise Exception(f"Requirement {job['requirement_id']} not found")
            
            # 候補者を取得（スクレイピング結果から）
            candidates, all_candidates, evaluated_candidate_ids = await self._get_candidates_for_job(job)
            
            print(f"Job {job_id}: Found {len(candidates)} candidates to process")
            print(f"Job details: client_id={job.get('client_id')}, requirement_id={job.get('requirement_id')}")
            
            # 進捗計算用の変数
            total_candidates_count = len(all_candidates)  # 要件に合致する全候補者数
            already_evaluated_count = len(evaluated_candidate_ids)  # 既に評価済みの数
            processed = 0  # 今回処理した数
            
            # 既に全て評価済みの場合
            if not candidates and total_candidates_count > 0:
                print(f"All {total_candidates_count} candidates already evaluated for job {job_id}")
                await self._update_job_status(job_id, 'completed', 100)
                return
            elif not candidates:
                print(f"No candidates found for job {job_id}")
                await self._update_job_status(job_id, 'completed', 100)
                return
            
            print(f"Progress calculation - Total: {total_candidates_count}, Already evaluated: {already_evaluated_count}, To process: {len(candidates)}")
            
            # 開始時の進捗率を計算して更新
            initial_progress = int((already_evaluated_count / total_candidates_count) * 100) if total_candidates_count > 0 else 0
            await self._update_job_status(job_id, 'running', initial_progress)
            print(f"Initial progress: {already_evaluated_count}/{total_candidates_count} = {initial_progress}%")
            
            # 各候補者を評価
            for candidate in candidates:
                try:
                    # ジョブのステータスを確認（停止要求チェック）
                    current_job = await self._get_job_details(job_id)
                    if current_job and current_job.get('status') != 'running':
                        print(f"Job {job_id} status is {current_job.get('status')}, stopping processing")
                        if current_job.get('status') == 'pending':
                            # 停止要求された場合
                            return
                        break
                    
                    # Supabaseから取得したデータを直接使用
                    resume_text = candidate.get('candidate_resume', '')
                    job_desc_text = self._format_job_description(requirement)
                    job_memo_text = self._format_job_memo(requirement)
                    
                    # レジュメが空の場合はスキップ
                    if not resume_text:
                        print(f"[AI Matching] Skipping candidate {candidate.get('id')} - no resume text")
                        processed += 1
                        continue
                    
                    # 構造化データの使用状況をログ出力
                    if requirement.get('structured_data', {}).get('basic_info'):
                        print(f"[AI Matching] Using new structured data format for requirement {requirement.get('id')}")
                    elif requirement.get('structured_data'):
                        print(f"[AI Matching] Using legacy structured data format for requirement {requirement.get('id')}")
                    else:
                        print(f"[AI Matching] No structured data found for requirement {requirement.get('id')}")
                    
                    # フォーマットされた内容のプレビューをログ出力
                    print(f"[AI Matching] Formatted job description preview (first 200 chars):")
                    print(f"  {job_desc_text[:200]}...")
                    print(f"[AI Matching] Formatted job memo preview (first 200 chars):")
                    print(f"  {job_memo_text[:200]}...")
                    
                    # レジュメを構造化
                    structured_resume_data = None
                    if self.resume_parser and resume_text:
                        try:
                            print(f"[AI Matching] Parsing resume for candidate {candidate.get('id')}")
                            structured_resume = await self.resume_parser.parse_resume(resume_text)
                            # StructuredResumeオブジェクトからディクショナリに変換
                            structured_resume_data = {
                                'basic_info': structured_resume.basic_info,
                                'raw_data': structured_resume.raw_data,
                                'matching_data': structured_resume.matching_data,
                                'metadata': structured_resume.metadata
                            }
                            print(f"[AI Matching] Resume parsed successfully - extracted {len(structured_resume.matching_data.get('skills_flat', []))} skills")
                        except Exception as e:
                            print(f"[AI Matching] Failed to parse resume: {e}")
                            # パースに失敗してもマッチングは続行
                    
                    # 再度停止チェック（AI処理の直前）
                    current_job = await self._get_job_details(job_id)
                    if current_job and current_job.get('status') != 'running':
                        print(f"Job {job_id} stopped before AI processing")
                        return
                    
                    # AIマッチング実行
                    if self.matcher and hasattr(self.matcher, 'match_candidate_direct'):
                        # 数値パラメータの安全な変換
                        def safe_int_convert(value):
                            if value is None:
                                return None
                            try:
                                return int(value)
                            except (ValueError, TypeError):
                                return None
                        
                        # 直接テキストを渡す
                        print(f"[AI Matching] Using real AI matching for candidate {candidate.get('id')}")
                        print(f"[AI Matching] Candidate info - age: {candidate.get('age')}, gender: {candidate.get('gender')}, company: {candidate.get('candidate_company')}")
                        
                        # 数値パラメータを安全に変換
                        candidate_age = safe_int_convert(candidate.get('age'))
                        enrolled_company_count = safe_int_convert(candidate.get('enrolled_company_count'))
                        
                        result = await asyncio.to_thread(
                            self.matcher.match_candidate_direct,
                            resume_text=resume_text,
                            job_description_text=job_desc_text,
                            job_memo_text=job_memo_text,
                            max_cycles=3,
                            # 候補者情報を追加
                            candidate_id=candidate.get('candidate_id'),
                            candidate_age=candidate_age,
                            candidate_gender=candidate.get('gender'),
                            candidate_company=candidate.get('candidate_company'),
                            enrolled_company_count=enrolled_company_count,
                            # 構造化データを追加
                            structured_job_data=requirement.get('structured_data'),
                            structured_resume_data=structured_resume_data
                        )
                        print(f"[AI Matching] Real result - Score: {result.get('final_score')}, Rec: {result.get('final_judgment', {}).get('recommendation')}")
                    else:
                        # マッチャーが初期化されていない場合のダミー結果
                        print(f"[AI Matching] Using dummy result - matcher: {self.matcher}, has method: {hasattr(self.matcher, 'match_candidate_direct') if self.matcher else False}")
                        result = self._generate_dummy_result()
                        print(f"[AI Matching] Dummy result - Score: {result.get('final_score')}, Rec: {result.get('final_judgment', {}).get('recommendation')}")
                    
                    # 結果を保存
                    await self._save_evaluation_result(job_id, candidate, result)
                    
                    processed += 1
                    
                    # 進捗更新（処理後に更新）
                    current_evaluated_count = already_evaluated_count + processed
                    progress = int((current_evaluated_count / total_candidates_count) * 100) if total_candidates_count > 0 else 100
                    await self._update_job_status(job_id, 'running', progress)
                    print(f"Progress updated: {current_evaluated_count}/{total_candidates_count} = {progress}%")
                    
                except Exception as e:
                    print(f"Error processing candidate {candidate.get('id')}: {e}")
                    # エラーでも続行（進捗はカウントしない）
            
            # ジョブ完了
            await self._update_job_status(job_id, 'completed', 100)
            
        except Exception as e:
            print(f"Error processing job {job_id}: {e}")
            await self._update_job_status(job_id, 'failed', error_message=str(e))
    
    async def _get_job_details(self, job_id: str) -> Optional[Dict]:
        """ジョブ詳細を取得"""
        response = self.supabase.table('jobs').select('*').eq('id', job_id).single().execute()
        return response.data
    
    async def _get_requirement(self, requirement_id: str) -> Optional[Dict]:
        """要件情報を取得"""
        response = self.supabase.table('job_requirements').select('*, client:clients(*)').eq('id', requirement_id).single().execute()
        requirement = response.data
        
        # デバッグ: 取得したデータを確認
        if requirement:
            print(f"[AI Matching] Requirement {requirement_id} data:")
            print(f"  - title: {requirement.get('title', 'N/A')}")
            print(f"  - job_description length: {len(requirement.get('job_description', '')) if requirement.get('job_description') else 0}")
            print(f"  - memo length: {len(requirement.get('memo', '')) if requirement.get('memo') else 0}")
            print(f"  - structured_data keys: {list(requirement.get('structured_data', {}).keys()) if requirement.get('structured_data') else []}")
        
        return requirement
    
    async def _get_candidates_for_job(self, job: Dict) -> Tuple[List[Dict], List[Dict], List[str]]:
        """ジョブに関連する候補者を取得
        
        Returns:
            Tuple[candidates(未評価), all_candidates(全候補者), evaluated_candidate_ids(評価済みID)]
        """
        # job_parameters から検索条件を取得
        params = job.get('parameters', {})
        job_id = job.get('id')
        
        print(f"Getting candidates for job: {job_id}")
        print(f"  client_id: {job.get('client_id')}")
        print(f"  requirement_id: {job.get('requirement_id')}")
        
        # まず、このジョブで既に評価済みの候補者IDを取得
        evaluated_response = self.supabase.table('ai_evaluations').select('candidate_id').eq('job_id', job_id).execute()
        evaluated_candidate_ids = [eval['candidate_id'] for eval in (evaluated_response.data or [])]
        
        print(f"  Already evaluated candidates: {len(evaluated_candidate_ids)}")
        
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
        
        # 全件取得（limit削除）
        query = query.order('scraped_at', desc=True)
        
        response = query.execute()
        all_candidates = response.data or []
        
        # 評価済みの候補者を除外
        candidates = [
            candidate for candidate in all_candidates 
            if candidate.get('id') not in evaluated_candidate_ids
        ]
        
        print(f"  Total candidates found: {len(all_candidates)}")
        print(f"  Unevaluated candidates: {len(candidates)}")
        if candidates:
            print(f"  First unevaluated candidate: {candidates[0].get('candidate_id')} - {candidates[0].get('candidate_company')}")
        
        return candidates, all_candidates, evaluated_candidate_ids
    
    
    def _format_job_description(self, requirement: Dict) -> str:
        """要件をジョブ記述文形式に変換（job_descriptionと構造化データを統合）"""
        sections = []
        
        # job_descriptionフィールドがある場合は、それを最初に追加
        if requirement.get('job_description'):
            print(f"[AI Matching] Including full job_description field: {len(requirement['job_description'])} chars")
            sections.append(requirement['job_description'])
            sections.append("\n" + "="*50 + "\n")  # セパレータ
        
        # 構造化データも追加（補足情報として）
        structured = requirement.get('structured_data', {})
        if structured:
            print(f"[AI Matching] Adding structured data as supplement")
            sections.append("【構造化情報】\n")
        
        # 新しい構造化データフォーマットの場合
        if 'basic_info' in structured:
            # 基本情報
            basic_info = structured.get('basic_info', {})
            if basic_info.get('title') or requirement.get('title'):
                sections.append(f"【ポジション】{basic_info.get('title', requirement.get('title', ''))}")
            if basic_info.get('company') or requirement.get('client', {}).get('name'):
                sections.append(f"【企業名】{basic_info.get('company', requirement.get('client', {}).get('name', ''))}")
            if basic_info.get('industry'):
                sections.append(f"【業界】{basic_info.get('industry')}")
            if basic_info.get('job_type'):
                sections.append(f"【職種】{basic_info.get('job_type')}")
            if basic_info.get('employment_type'):
                sections.append(f"【雇用形態】{basic_info.get('employment_type')}")
            if basic_info.get('location'):
                sections.append(f"【勤務地】{basic_info.get('location')}")
            
            # 必須要件
            if structured.get('requirements', {}).get('must_have'):
                must_have_items = []
                for req in structured['requirements']['must_have']:
                    must_have_items.append(f"- [{req['category']}] {req['item']}")
                sections.append(f"【必須要件】\n" + '\n'.join(must_have_items))
            
            # 歓迎要件
            if structured.get('requirements', {}).get('nice_to_have'):
                nice_to_have_items = []
                for req in structured['requirements']['nice_to_have']:
                    nice_to_have_items.append(f"- [{req['category']}] {req['item']}")
                sections.append(f"【歓迎要件】\n" + '\n'.join(nice_to_have_items))
            
            # 評価ポイント
            if structured.get('evaluation_points'):
                eval_points = []
                for point in structured['evaluation_points']:
                    eval_points.append(f"- {point['name']}: {point['description']}")
                sections.append(f"【評価ポイント】\n" + '\n'.join(eval_points))
        
        # 従来の構造化データフォーマットの場合（後方互換性）
        else:
            sections.append(f"【ポジション】{requirement.get('title', '')}")
            
            if requirement.get('client', {}).get('name'):
                sections.append(f"【企業名】{requirement['client']['name']}")
            
            if structured.get('position_details'):
                sections.append(f"【ポジション詳細】\n{structured['position_details']}")
            
            if structured.get('required_experience'):
                sections.append(f"【必須経験】\n{structured['required_experience']}")
            
            if structured.get('preferred_experience'):
                sections.append(f"【歓迎経験】\n{structured['preferred_experience']}")
            
            if structured.get('job_description'):
                sections.append(f"【職務内容】\n{structured['job_description']}")
        
        # descriptionフィールドがある場合は追加（フォールバック）
        if not structured and requirement.get('description'):
            sections.append(f"【詳細説明】\n{requirement['description']}")
        
        return '\n\n'.join(sections)
    
    def _format_job_memo(self, requirement: Dict) -> str:
        """要件のメモ情報を抽出（新しい構造化データ対応）"""
        sections = []
        
        structured = requirement.get('structured_data', {})
        
        # 新しい構造化データフォーマットの場合
        if 'basic_info' in structured:
            # キーワード情報
            if structured.get('keywords'):
                keywords = structured['keywords']
                keyword_sections = []
                
                if keywords.get('technical'):
                    keyword_sections.append(f"技術: {', '.join(keywords['technical'])}")
                if keywords.get('soft_skills'):
                    keyword_sections.append(f"ソフトスキル: {', '.join(keywords['soft_skills'])}")
                if keywords.get('domain'):
                    keyword_sections.append(f"ドメイン知識: {', '.join(keywords['domain'])}")
                if keywords.get('company_culture'):
                    keyword_sections.append(f"企業文化: {', '.join(keywords['company_culture'])}")
                
                if keyword_sections:
                    sections.append(f"【重要キーワード】\n" + '\n'.join(keyword_sections))
            
            # RAGパラメータから追加情報を抽出
            if structured.get('rag_parameters', {}).get('filters'):
                filters = structured['rag_parameters']['filters']
                filter_info = []
                
                if filters.get('industry'):
                    filter_info.append(f"業界: {', '.join(filters['industry'])}")
                if filters.get('job_type'):
                    filter_info.append(f"職種: {', '.join(filters['job_type'])}")
                if filters.get('skills'):
                    filter_info.append(f"スキル: {', '.join(filters['skills'])}")
                
                if filter_info:
                    sections.append(f"【検索フィルター】\n" + '\n'.join(filter_info))
            
            # 元の求人メモがある場合は追加
            if requirement.get('memo'):
                sections.append(f"【求人メモ】\n{requirement['memo']}")
        
        # 従来の構造化データフォーマットの場合（後方互換性）
        else:
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
        
        # memoフィールドがある場合は追加（フォールバック）
        if not sections and requirement.get('memo'):
            sections.append(requirement['memo'])
        
        return '\n\n'.join(sections)
    
    async def _save_evaluation_result(self, job_id: str, candidate: Dict, result: Dict):
        """評価結果を保存"""
        # 候補者から requirement_id を取得
        requirement_id = candidate.get('requirement_id')
        
        # 評価結果からデータを抽出
        final_judgment = result.get('final_judgment', {})
        
        evaluation_data = {
            'id': str(uuid.uuid4()),
            'job_id': job_id,  # jobs.idを参照（search_idから名称変更）
            'candidate_id': candidate['id'],
            'requirement_id': requirement_id,
            
            # スコアとステータス（シンプル化）
            'score': result.get('final_score', 0),
            'recommendation': final_judgment.get('recommendation', 'D'),
            'confidence': self._convert_confidence(result.get('final_confidence', 'Low')),
            
            # 評価詳細
            'strengths': final_judgment.get('strengths', []),
            'concerns': final_judgment.get('concerns', []),
            'reason': final_judgment.get('reason', ''),
            'summary': result.get('evaluation_summary', ''),
            'overall_assessment': final_judgment.get('overall_assessment', ''),
            
            # メタデータ
            'raw_response': json.dumps(result, ensure_ascii=False) if result else None,
            'evaluation_cycles': result.get('total_cycles', 0),
            'web_searches': result.get('total_searches', 0),
            'model_version': result.get('model_version', 'gemini-2.0-flash'),
            'prompt_version': '1.0',
            
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
print("[AI Matching] Creating singleton instance...")
ai_matching_service = AIMatchingService()
print(f"[AI Matching] Singleton created - matcher status: {ai_matching_service.matcher is not None}")