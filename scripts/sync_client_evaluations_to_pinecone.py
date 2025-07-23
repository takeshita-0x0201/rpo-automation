"""
クライアント評価をSupabaseからPineconeへ同期するバッチ処理
定期的に実行してクライアントフィードバックをRAGシステムに反映
"""
import os
import sys
from datetime import datetime
import json
from typing import List, Dict, Optional
import asyncio
from dotenv import load_dotenv
import time
from tenacity import retry, stop_after_attempt, wait_exponential

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 環境変数を読み込む
load_dotenv()

# 必要なモジュールをインポート
from supabase import create_client, Client
import google.generativeai as genai
try:
    from pinecone import Pinecone
except ImportError:
    import pinecone
    Pinecone = None

class ClientEvaluationSyncer:
    """クライアント評価をPineconeに同期"""
    
    def __init__(self):
        # Supabaseクライアントの初期化
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_ANON_KEY")
        if not supabase_url or not supabase_key:
            raise ValueError("Supabase credentials not found in environment")
        
        self.supabase: Client = create_client(supabase_url, supabase_key)
        
        # Gemini APIの設定
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not gemini_api_key:
            raise ValueError("Gemini API key not found in environment")
        
        genai.configure(api_key=gemini_api_key)
        self.embedding_model = "models/text-embedding-004"
        
        # Pineconeの設定
        pinecone_api_key = os.getenv("PINECONE_API_KEY")
        if not pinecone_api_key:
            raise ValueError("Pinecone API key not found in environment")
        
        if Pinecone:
            self.pc = Pinecone(api_key=pinecone_api_key)
        else:
            pinecone.init(api_key=pinecone_api_key)
            
        self.index_name = "recruitment-matching"
        self.namespace = "historical-cases"
        
        if Pinecone:
            self.index = self.pc.Index(self.index_name)
        else:
            self.index = pinecone.Index(self.index_name)
    
    async def sync_evaluations(self, batch_size: int = 100, max_retries: int = 3):
        """未同期の評価をPineconeに同期（エラーハンドリング強化版）"""
        print(f"\n=== クライアント評価同期開始: {datetime.now().isoformat()} ===")
        
        # 未同期データを取得
        unsync_data = self._fetch_unsync_evaluations(batch_size)
        if not unsync_data:
            print("同期対象のデータがありません")
            return
        
        print(f"同期対象: {len(unsync_data)}件")
        
        # バッチ処理の準備
        success_count = 0
        failed_items = []
        batch_vectors = []
        
        # 各評価を処理
        for i, evaluation in enumerate(unsync_data):
            try:
                # ベクトルを準備（まだアップロードしない）
                vectors = await self._prepare_evaluation_vectors(evaluation)
                batch_vectors.extend(vectors)
                
                # バッチサイズに達したらアップロード
                if len(batch_vectors) >= 100 or i == len(unsync_data) - 1:
                    await self._upsert_batch_with_retry(batch_vectors, max_retries)
                    
                    # 同期フラグを更新
                    for j in range(len(batch_vectors) // 3):  # 3ベクトル/評価
                        eval_id = unsync_data[success_count + j]['id']
                        self._update_sync_status(eval_id)
                        
                    success_count += len(batch_vectors) // 3
                    batch_vectors = []
                    
                    # API制限対策
                    await asyncio.sleep(0.1)
                    
            except Exception as e:
                failed_items.append({
                    'id': evaluation['id'],
                    'error': str(e)
                })
                print(f"✗ 処理失敗: {evaluation['id']} - {str(e)}")
        
        # 結果サマリー
        print(f"\n同期完了サマリー:")
        print(f"  成功: {success_count}/{len(unsync_data)}件")
        print(f"  失敗: {len(failed_items)}件")
        
        if failed_items:
            print("\n失敗した項目:")
            for item in failed_items[:5]:  # 最初の5件のみ表示
                print(f"  - {item['id']}: {item['error']}")
            if len(failed_items) > 5:
                print(f"  ... 他 {len(failed_items) - 5}件")
    
    def _fetch_unsync_evaluations(self, limit: int) -> List[Dict]:
        """未同期の評価データを取得"""
        response = self.supabase.table('ai_evaluations')\
            .select("""
                *,
                candidate:candidates(*),
                requirement:job_requirements(*, client:clients(*))
            """)\
            .eq('synced_to_pinecone', False)\
            .not_.is_('client_evaluation', 'null')\
            .order('created_at')\
            .limit(limit)\
            .execute()
        
        return response.data if response.data else []
    
    async def _prepare_evaluation_vectors(self, evaluation: Dict) -> List[Dict]:
        """評価データからベクトルを準備（アップロードはしない）"""
        # ケースIDを生成
        case_id = f"webapp_{evaluation['id']}"
        
        # ベクトル用のテキストを生成
        vectors_data = self._prepare_vectors_data(evaluation)
        
        # 3種類のベクトルを生成
        vectors = []
        
        # 1. Combined vector (統合ベクトル)
        combined_text = self._create_combined_text(vectors_data)
        combined_embedding = await self._generate_embedding(combined_text)
        
        # 2. Job side vector (求人側ベクトル)
        job_text = self._create_job_text(vectors_data)
        job_embedding = await self._generate_embedding(job_text)
        
        # 3. Candidate vector (候補者側ベクトル)
        candidate_text = self._create_candidate_text(vectors_data)
        candidate_embedding = await self._generate_embedding(candidate_text)
        
        # 拡張メタデータの準備
        metadata_base = self._create_enhanced_metadata(evaluation, case_id)
        
        # ベクトルを返す（アップロードはしない）
        return [
            {
                'id': f"{case_id}_combined",
                'values': combined_embedding,
                'metadata': {**metadata_base, 'vector_type': 'combined'}
            },
            {
                'id': f"{case_id}_job_side",
                'values': job_embedding,
                'metadata': {**metadata_base, 'vector_type': 'job_side'}
            },
            {
                'id': f"{case_id}_candidate",
                'values': candidate_embedding,
                'metadata': {**metadata_base, 'vector_type': 'candidate'}
            }
        ]
    
    def _prepare_vectors_data(self, evaluation: Dict) -> Dict:
        """ベクトル生成用のデータを準備"""
        requirement = evaluation['requirement']
        candidate = evaluation['candidate']
        
        # 求人情報のフォーマット
        job_description = self._format_job_description(requirement)
        job_memo = self._format_job_memo(requirement)
        
        # 評価結果のフォーマット
        evaluation_result = self._format_evaluation_result(evaluation)
        
        return {
            'position': requirement['title'],
            'job_description': job_description,
            'job_memo': job_memo,
            'candidate_info': candidate.get('candidate_resume', ''),
            'evaluation_result': evaluation_result
        }
    
    def _format_job_description(self, requirement: Dict) -> str:
        """求人情報をフォーマット"""
        sections = []
        sections.append(f"【ポジション】{requirement.get('title', '')}")
        
        if requirement.get('client', {}).get('name'):
            sections.append(f"【企業名】{requirement['client']['name']}")
        
        structured = requirement.get('structured_data', {})
        
        if structured.get('position_details'):
            sections.append(f"【ポジション詳細】\n{structured['position_details']}")
        
        if structured.get('required_experience'):
            sections.append(f"【必須経験】\n{structured['required_experience']}")
        
        if structured.get('job_description'):
            sections.append(f"【職務内容】\n{structured['job_description']}")
        
        return '\n\n'.join(sections)
    
    def _format_job_memo(self, requirement: Dict) -> str:
        """求人メモをフォーマット"""
        sections = []
        structured = requirement.get('structured_data', {})
        
        if structured.get('job_memo'):
            sections.append(structured['job_memo'])
        
        if structured.get('salary_range'):
            sections.append(f"【想定年収】{structured['salary_range']}")
        
        return '\n\n'.join(sections)
    
    def _format_evaluation_result(self, evaluation: Dict) -> str:
        """評価結果をフォーマット"""
        sections = []
        
        sections.append(f"【AIマッチングスコア】{evaluation['score']}/100")
        sections.append(f"【AI推奨度】{evaluation['recommendation']}")
        sections.append(f"【確信度】{evaluation['confidence']}")
        
        if evaluation.get('strengths'):
            sections.append(f"【強み】\n" + '\n'.join(f"- {s}" for s in evaluation['strengths']))
        
        if evaluation.get('concerns'):
            sections.append(f"【懸念点】\n" + '\n'.join(f"- {c}" for c in evaluation['concerns']))
        
        if evaluation.get('overall_assessment'):
            sections.append(f"【総合評価】\n{evaluation['overall_assessment']}")
        
        # クライアント評価を追加
        sections.append(f"\n【クライアント評価】{evaluation['client_evaluation']}")
        if evaluation.get('client_comment'):
            sections.append(f"【クライアントコメント】\n{evaluation['client_comment']}")
        
        return '\n\n'.join(sections)
    
    def _create_combined_text(self, data: Dict) -> str:
        """統合ベクトル用テキスト"""
        return f"""
ポジション: {data['position']}

{data['job_description']}

{data['job_memo']}

候補者情報:
{data['candidate_info']}

評価結果:
{data['evaluation_result']}
"""
    
    def _create_job_text(self, data: Dict) -> str:
        """求人側ベクトル用テキスト"""
        return f"""
ポジション: {data['position']}

{data['job_description']}

{data['job_memo']}
"""
    
    def _create_candidate_text(self, data: Dict) -> str:
        """候補者側ベクトル用テキスト"""
        return f"""
候補者情報:
{data['candidate_info']}

評価結果:
{data['evaluation_result']}
"""
    
    async def _generate_embedding(self, text: str) -> List[float]:
        """テキストからベクトルを生成"""
        result = genai.embed_content(
            model=self.embedding_model,
            content=text,
            task_type="retrieval_document"
        )
        return result['embedding']
    
    def _truncate_text(self, text: str, max_length: int) -> str:
        """テキストを指定長に切り詰める"""
        if not text:
            return ""
        return text[:max_length] if len(text) > max_length else text
    
    def _update_sync_status(self, evaluation_id: str):
        """同期ステータスを更新"""
        self.supabase.table('ai_evaluations')\
            .update({
                'synced_to_pinecone': True,
                'synced_at': datetime.now().isoformat()
            })\
            .eq('id', evaluation_id)\
            .execute()
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _upsert_batch_with_retry(self, vectors: List[Dict], max_retries: int):
        """バッチでベクトルをアップサート（リトライ機能付き）"""
        try:
            self.index.upsert(vectors=vectors, namespace=self.namespace)
        except Exception as e:
            print(f"Upsert failed: {str(e)}, retrying...")
            raise
    
    def _create_enhanced_metadata(self, evaluation: Dict, case_id: str) -> Dict:
        """拡張メタデータの作成"""
        requirement = evaluation.get('requirement', {})
        candidate = evaluation.get('candidate', {})
        
        # 基本メタデータ
        metadata = {
            'case_id': case_id,
            'created_at': evaluation['created_at'],
            
            # ポジション情報
            'position': requirement.get('title', ''),
            'company': requirement.get('client', {}).get('name', ''),
            'department': requirement.get('department', ''),
            'job_type': requirement.get('job_type', ''),
            
            # 候補者情報
            'candidate_id': candidate.get('id', ''),
            'candidate_company': candidate.get('candidate_company', ''),
            'years_of_experience': candidate.get('years_of_experience', 0),
            
            # AI評価
            'ai_score': evaluation.get('score', 0),
            'ai_recommendation': evaluation.get('recommendation', ''),
            'ai_confidence': evaluation.get('confidence', ''),
            
            # クライアント評価
            'client_evaluation': evaluation.get('client_evaluation', ''),
            'client_comment': self._truncate_text(evaluation.get('client_comment', ''), 500),
            
            # 評価の一致度
            'evaluation_match': evaluation.get('recommendation', '') == evaluation.get('client_evaluation', ''),
            'score_category': self._categorize_score(evaluation.get('score', 0)),
            
            # 検索用フィールド
            'has_client_feedback': bool(evaluation.get('client_evaluation')),
            'is_successful': evaluation.get('client_evaluation', '') in ['A', 'B'],
            'evaluation_period': self._get_period(evaluation.get('created_at', '')),
            
            # 品質指標
            'has_detailed_feedback': len(evaluation.get('client_comment', '')) > 50,
            'data_source': 'webapp_sync',
            'sync_version': '2.0'  # メタデータ構造のバージョン
        }
        
        # 構造化データからの追加情報
        structured = requirement.get('structured_data', {})
        if structured:
            metadata['required_skills_count'] = len(structured.get('required_skills', []))
            metadata['salary_range'] = structured.get('salary_range', '')
            metadata['remote_option'] = structured.get('remote_option', False)
        
        return metadata
    
    def _categorize_score(self, score: int) -> str:
        """スコアをカテゴリに分類"""
        if score >= 90:
            return 'excellent'
        elif score >= 80:
            return 'good'
        elif score >= 70:
            return 'fair'
        elif score >= 60:
            return 'borderline'
        else:
            return 'low'
    
    def _get_period(self, timestamp: str) -> str:
        """タイムスタンプから期間を取得"""
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m')
        except:
            return 'unknown'

async def main():
    """メイン処理"""
    try:
        syncer = ClientEvaluationSyncer()
        await syncer.sync_evaluations()
    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())