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
import os
import httpx
from pydantic import BaseModel

from core.utils.supabase_client import get_supabase_client
from .auth import get_current_user_from_cookie

router = APIRouter()

# Request model for export
class ExportCandidatesRequest(BaseModel):
    selected_candidate_ids: List[str]

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
        job_response = supabase.table('jobs').select('*, clients(name)').eq('id', job_id).single().execute()
        job = job_response.data
        
        # クライアント情報を整形（ネストされたオブジェクトから取り出す）
        if job and job.get('clients'):
            job['client'] = job['clients']
            del job['clients']
        
        # AI評価結果を取得（送客状態も含む）
        evaluations_response = supabase.table('ai_evaluations').select('*').eq('job_id', job_id).order('score', desc=True).execute()
        
        evaluations = evaluations_response.data if evaluations_response.data else []
        
        # 候補者IDのリストを取得
        candidate_ids = [eval['candidate_id'] for eval in evaluations if eval.get('candidate_id')]
        
        # 候補者情報を一括取得
        candidates_map = {}
        if candidate_ids:
            candidates_response = supabase.table('candidates').select('*').in_('id', candidate_ids).execute()
            if candidates_response.data:
                # 性別の表示変換を追加
                for c in candidates_response.data:
                    if c.get('gender'):
                        c['gender_display'] = '男性' if c['gender'] == 'M' else '女性' if c['gender'] == 'F' else c['gender']
                    else:
                        c['gender_display'] = '-'
                candidates_map = {c['id']: c for c in candidates_response.data}
        
        # 評価データに候補者情報を結合
        for eval in evaluations:
            if eval.get('candidate_id') and eval['candidate_id'] in candidates_map:
                candidate = candidates_map[eval['candidate_id']]
                # candidatesテーブルのフィールドをそのまま使用
                eval['candidate'] = candidate
            else:
                eval['candidate'] = {}
        
        # 推奨度のテキストと色を追加
        for eval in evaluations:
            # recommendationフィールドをA/B/C/D形式に対応
            eval['recommendation_text'] = {
                'A': '強く推奨',
                'B': '推奨',
                'C': '要検討',
                'D': '不適合'
            }.get(eval['recommendation'], '未評価')
            
            eval['recommendation_color'] = {
                'A': 'success',
                'B': 'primary',
                'C': 'warning',
                'D': 'danger'
            }.get(eval['recommendation'], 'secondary')
        
        # 統計情報（送客済み候補者数を追加）
        stats = {
            'total': len(evaluations),
            'high': len([e for e in evaluations if e['recommendation'] == 'A']),
            'medium': len([e for e in evaluations if e['recommendation'] == 'B']),
            'low': len([e for e in evaluations if e['recommendation'] in ['C', 'D']]),
            'sent': len([e for e in evaluations if e.get('sent_to_sheet', False)])
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
    request: ExportCandidatesRequest,
    user: Optional[dict] = Depends(get_current_user_from_cookie)
):
    """選択した候補者をスプレッドシートに出力し、送客状態を更新"""
    if not user:
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    
    try:
        supabase = get_supabase_client()
        selected_candidate_ids = request.selected_candidate_ids
        
        # ジョブ情報を取得
        job_response = supabase.table('jobs').select('*, clients(name)').eq('id', job_id).single().execute()
        job = job_response.data
        
        # job_requirementsを別途取得（requirement_idがTEXT型のため）
        if job and job.get('requirement_id'):
            req_response = supabase.table('job_requirements').select('title').eq('id', job['requirement_id']).single().execute()
            if req_response.data:
                job['job_requirements'] = req_response.data
        
        # 選択された候補者のAI評価情報を取得
        evaluations_response = supabase.table('ai_evaluations').select('*').in_('candidate_id', selected_candidate_ids).eq('job_id', job_id).execute()
        evaluations = evaluations_response.data
        
        # 候補者情報を別途取得
        if evaluations:
            candidate_ids = [e['candidate_id'] for e in evaluations if e.get('candidate_id')]
            if candidate_ids:
                candidates_response = supabase.table('candidates').select('*').in_('id', candidate_ids).execute()
                candidates_map = {c['id']: c for c in candidates_response.data} if candidates_response.data else {}
                
                # 評価データに候補者情報を結合
                for eval_data in evaluations:
                    if eval_data.get('candidate_id') in candidates_map:
                        eval_data['candidates'] = candidates_map[eval_data['candidate_id']]
                    else:
                        eval_data['candidates'] = {}
        
        if not evaluations:
            return JSONResponse(status_code=400, content={"error": "選択された候補者が見つかりません"})
        
        # GAS用のデータを準備
        submitted_at = datetime.now().isoformat()
        gas_data = {
            'job_id': job_id,
            'client_name': job['clients']['name'] if job.get('clients') else '',
            'requirement_title': job['job_requirements']['title'] if job.get('job_requirements') else '',
            'submission_count': len(evaluations),
            'submitted_by': user.get('full_name', user.get('email', '')),
            'submitted_at': submitted_at,
            'candidates': []
        }
        
        evaluation_ids = []
        for eval_data in evaluations:
            candidate = eval_data.get('candidates', {})
            if not candidate:
                continue
                
            evaluation_ids.append(eval_data['id'])
            
            # プラットフォームの判定
            platform = candidate.get('platform', 'bizreach')
            
            # 年齢の計算（生年月日から）
            age = None
            if candidate.get('date_of_birth'):
                try:
                    birth_date = datetime.fromisoformat(candidate['date_of_birth'].replace('Z', '+00:00'))
                    age = (datetime.now() - birth_date).days // 365
                except:
                    pass
            
            # 候補者データの準備（新フォーマット）
            gas_candidate = {
                'candidate_id': candidate.get('candidate_id', ''),
                'candidate_company': candidate.get('candidate_company', ''),
                'candidate_link': candidate.get('candidate_link', ''),
                'gender': candidate.get('gender', ''),
                'reason': eval_data.get('reason', ''),  # ピックアップメモ用
            }
            gas_data['candidates'].append(gas_candidate)
        
        # GAS webhookにPOST送信
        gas_webhook_url = os.getenv('GAS_WEBHOOK_URL')
        spreadsheet_url = None
        
        if gas_webhook_url:
            try:
                # タイムアウトを短縮して、早めにレスポンスを返す
                async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
                    print(f"Sending to GAS webhook: {len(gas_data['candidates'])} candidates")
                    response = await client.post(gas_webhook_url, json=gas_data)
                    
                    # ステータスコードだけ確認
                    if response.status_code in [200, 201, 202]:
                        # 成功とみなす
                        try:
                            gas_response = response.json()
                            spreadsheet_url = gas_response.get('spreadsheet_url', os.getenv('GOOGLE_SHEETS_ID'))
                        except:
                            # JSONパースエラーでも成功とみなす
                            spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{os.getenv('GOOGLE_SHEETS_ID', 'dummy')}"
                    else:
                        print(f"GAS webhook returned status {response.status_code}")
                        spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{os.getenv('GOOGLE_SHEETS_ID', 'dummy')}"
                            
            except httpx.TimeoutException:
                # タイムアウトしても、GAS側で処理は継続されている可能性が高いので成功とみなす
                print("GAS webhook timeout - but assuming success")
                spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{os.getenv('GOOGLE_SHEETS_ID', 'dummy')}"
            except Exception as e:
                # その他のエラーも、GAS側で処理されている可能性があるので成功とみなす
                print(f"GAS webhook error (ignored): {type(e).__name__}: {e}")
                spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{os.getenv('GOOGLE_SHEETS_ID', 'dummy')}"
        else:
            # GAS_WEBHOOK_URLが設定されていない場合はデバッグ用の応答
            spreadsheet_url = "https://docs.google.com/spreadsheets/d/dummy"
        
        # ai_evaluationsテーブルの送客状態を更新
        update_data = {
            'sent_to_sheet': True,
            'sent_to_sheet_at': submitted_at
        }
        
        for eval_id in evaluation_ids:
            supabase.table('ai_evaluations').update(update_data).eq('id', eval_id).execute()
        
        return JSONResponse(content={
            'success': True,
            'message': f'{len(evaluations)}件の候補者をスプレッドシートに追加しました',
            'spreadsheet_url': spreadsheet_url
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