"""
候補者管理ルーター
AIマッチング完了後の候補者表示と選択機能
"""
from fastapi import APIRouter, Request, HTTPException, Depends, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import pathlib

# テンプレートの設定
base_dir = pathlib.Path(__file__).parent.parent
templates = Jinja2Templates(directory=str(base_dir / "templates"))
from typing import List, Optional
import json
from datetime import datetime

from src.utils.supabase_client import get_supabase_client
from src.web.routers.auth import get_current_user_from_cookie

router = APIRouter()

@router.get("/job/{job_id}/candidates", response_class=HTMLResponse)
async def job_candidates_list(
    request: Request, 
    job_id: str,
    user: Optional[dict] = Depends(get_current_user_from_cookie)
):
    """ジョブ完了後の候補者一覧表示"""
    if not user:
        return RedirectResponse(url="/login?error=Unauthorized", status_code=303)
    
    try:
        supabase = get_supabase_client()
        
        # ジョブ情報を取得
        job_response = supabase.table('jobs').select('*, client:clients(name)').eq('id', job_id).single().execute()
        job = job_response.data
        
        # AI評価結果を取得（候補者情報と結合）
        evaluations_response = supabase.table('ai_evaluations').select('''
            *,
            candidate:candidates(*)
        ''').eq('search_id', job_id).order('ai_score', desc=True).execute()
        
        evaluations = evaluations_response.data if evaluations_response.data else []
        
        # 推奨度のテキストと色を追加
        for eval in evaluations:
            eval['recommendation_text'] = {
                'high': '強く推奨',
                'medium': '推奨',
                'low': '要検討'
            }.get(eval['recommendation'], '未評価')
            
            eval['recommendation_color'] = {
                'high': 'success',
                'medium': 'warning',
                'low': 'secondary'
            }.get(eval['recommendation'], 'secondary')
        
        # 統計情報
        stats = {
            'total': len(evaluations),
            'high': len([e for e in evaluations if e['recommendation'] == 'high']),
            'medium': len([e for e in evaluations if e['recommendation'] == 'medium']),
            'low': len([e for e in evaluations if e['recommendation'] == 'low'])
        }
        
        return templates.TemplateResponse("admin/job_candidates.html", {
            "request": request,
            "current_user": user,
            "job": job,
            "evaluations": evaluations,
            "stats": stats
        })
        
    except Exception as e:
        print(f"Error loading candidates: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/job/{job_id}/export-selected")
async def export_selected_candidates(
    job_id: str,
    selected_candidate_ids: List[str],
    user: Optional[dict] = Depends(get_current_user_from_cookie)
):
    """選択した候補者をcandidate_submissionsに保存し、GASに送信"""
    if not user:
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    
    try:
        supabase = get_supabase_client()
        
        # 選択された候補者の情報を取得
        candidates_response = supabase.table('candidates').select('*').in_('id', selected_candidate_ids).execute()
        candidates = candidates_response.data
        
        # AI評価情報を取得
        evaluations_response = supabase.table('ai_evaluations').select('*').in_('candidate_id', selected_candidate_ids).execute()
        evaluations = {e['candidate_id']: e for e in evaluations_response.data}
        
        # ジョブ情報を取得
        job_response = supabase.table('jobs').select('*, client:clients(*), requirement:job_requirements(*)').eq('id', job_id).single().execute()
        job = job_response.data
        
        # candidate_submissionsに記録
        submissions = []
        for candidate in candidates:
            submission = {
                'job_id': job_id,
                'client_id': job['client_id'],
                'candidate_id': candidate['id'],
                'status': 'submitted',
                'submitted_by': user['id'],
                'submission_data': {
                    'candidate': candidate,
                    'evaluation': evaluations.get(candidate['id']),
                    'submitted_at': datetime.now().isoformat()
                }
            }
            submissions.append(submission)
        
        # バッチ挿入
        submission_response = supabase.table('candidate_submissions').insert(submissions).execute()
        
        # GAS用のデータを準備
        gas_data = {
            'job_id': job_id,
            'client_name': job['client']['name'],
            'requirement_title': job['requirement']['title'],
            'submission_count': len(candidates),
            'submitted_by': user['full_name'],
            'candidates': []
        }
        
        for candidate in candidates:
            eval_data = evaluations.get(candidate['id'], {})
            gas_data['candidates'].append({
                'candidate_id': candidate['candidate_id'],
                'candidate_company': candidate['candidate_company'],
                'platform': candidate['platform'],
                'ai_score': eval_data.get('ai_score', 0),
                'recommendation': eval_data.get('recommendation', ''),
                'match_reasons': eval_data.get('match_reasons', []),
                'concerns': eval_data.get('concerns', []),
                'candidate_link': candidate['candidate_link'],
                'resume_summary': candidate['candidate_resume'][:500] if candidate.get('candidate_resume') else ''
            })
        
        # TODO: GAS webhookにPOST送信
        # gas_webhook_url = os.getenv('GAS_WEBHOOK_URL')
        # if gas_webhook_url:
        #     response = requests.post(gas_webhook_url, json=gas_data)
        
        return JSONResponse(content={
            'success': True,
            'message': f'{len(candidates)}件の候補者を送客リストに追加しました',
            'submission_count': len(candidates),
            'gas_data': gas_data  # デバッグ用
        })
        
    except Exception as e:
        print(f"Error exporting candidates: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@router.get("/submissions/history", response_class=HTMLResponse)
async def submission_history(
    request: Request,
    user: Optional[dict] = Depends(get_current_user_from_cookie)
):
    """送客履歴の表示"""
    if not user:
        return RedirectResponse(url="/login?error=Unauthorized", status_code=303)
    
    try:
        supabase = get_supabase_client()
        
        # 送客履歴を取得
        submissions_response = supabase.table('candidate_submissions').select('''
            *,
            job:jobs(*),
            client:clients(name)
        ''').order('submitted_at', desc=True).limit(100).execute()
        
        submissions = submissions_response.data if submissions_response.data else []
        
        return templates.TemplateResponse("admin/submission_history.html", {
            "request": request,
            "current_user": user,
            "submissions": submissions
        })
        
    except Exception as e:
        print(f"Error loading submission history: {e}")
        raise HTTPException(status_code=500, detail=str(e))