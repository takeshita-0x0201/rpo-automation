import pathlib
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
import uuid
from datetime import datetime
import json # 追加
from .auth import get_current_user_from_cookie

async def get_current_admin_user(user: dict = Depends(get_current_user_from_cookie)) -> dict:
    if not user or user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    return user
from core.utils.supabase_client import get_supabase_client
from core.utils.supabase_service import get_supabase_service_client

def get_db():
    """データベースクライアントを取得（RLSバイパス）"""
    return get_supabase_service_client()

router = APIRouter()
templates_path = pathlib.Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_path))

@router.get("/admin/requirements", response_class=HTMLResponse)
async def requirements_list(request: Request, user=Depends(get_current_admin_user), db=Depends(get_db)):
    """採用要件一覧ページ"""
    try:
        # 1. クライアント一覧を取得
        clients_response = db.table('clients').select('id, name').execute()
        if not clients_response.data:
            clients_map = {}
        else:
            clients_map = {str(client['id']): client['name'] for client in clients_response.data}

        # 2. 採用要件一覧を取得
        req_response = db.table('job_requirements').select('*').order('requirement_id', desc=False).execute()
        
        if not req_response.data:
            requirements = []
        else:
            requirements = req_response.data
            
            # 3. Pythonでクライアント名を紐付け
            for req in requirements:
                req['client_name'] = clients_map.get(str(req['client_id']), 'N/A')

    except Exception as e:
        requirements = []

    return templates.TemplateResponse("admin/requirements.html", {
        "request": request,
        "current_user": user,
        "requirements": requirements,
        "page": "requirements"
    })

@router.get("/admin/requirements/new", response_class=HTMLResponse)
async def requirements_new(request: Request, user=Depends(get_current_admin_user), db=Depends(get_db)):
    """新規採用要件作成ページ"""
    try:
        clients_response = db.table('clients').select('id, name').eq('is_active', True).execute()
        clients = clients_response.data
    except Exception as e:
        clients = []

    return templates.TemplateResponse("admin/requirements_new.html", {
        "request": request,
        "current_user": user,
        "clients": clients,
        "page": "requirements"
    })

@router.post("/admin/requirements/create")
async def create_requirement(
    request: Request,
    client_id: str = Form(...),
    position: str = Form(...),
    job_description: str = Form(...),
    requirement_memo: str = Form(...),
    structured_data: str = Form(...),
    user=Depends(get_current_admin_user),
    db=Depends(get_db)
):
    """採用要件を作成"""
    try:
        # requirement_idの連番を生成
        requirement_id = None
        try:
            result = db.rpc('get_next_requirement_id').execute()
            if result.data:
                requirement_id = result.data
            else:
                raise Exception("Failed to generate requirement_id")
        except Exception as e:
            print(f"Error generating requirement_id with RPC: {e}")
            # フォールバック: 最大値を取得して次の番号を生成
            try:
                max_response = db.table('job_requirements').select('requirement_id').like('requirement_id', 'req-%').order('requirement_id', desc=True).limit(1).execute()
                
                if max_response.data and len(max_response.data) > 0:
                    last_id = max_response.data[0]['requirement_id']
                    # req-001 形式から数値を抽出
                    if last_id and last_id.startswith('req-'):
                        last_num = int(last_id.split('-')[1])
                        next_num = last_num + 1
                    else:
                        next_num = 1
                else:
                    next_num = 1
                
                requirement_id = f"req-{str(next_num).zfill(3)}"
            except Exception as fallback_error:
                print(f"Fallback also failed: {fallback_error}")
                # 最終手段: タイムスタンプベース
                import uuid
                requirement_id = f"req-temp-{str(uuid.uuid4())[:8]}"
        
        # structured_dataが空文字列の場合のハンドリング
        if not structured_data.strip():
            parsed_structured_data = {}
        else:
            parsed_structured_data = json.loads(structured_data)
        
        # 採用要件を作成（job_requirementsテーブルのみ使用）
        new_requirement = {
            "client_id": client_id,
            "title": position,  # ポジションをタイトルとして使用
            "description": f"【求人票】\n{job_description}\n\n【求人メモ】\n{requirement_memo}",  # 全ての情報をdescriptionに格納
            "structured_data": parsed_structured_data,
            "created_by": user['id'],
            # 追加カラム
            "requirement_id": requirement_id,  # 生成したreq-001形式のID
            "memo": requirement_memo.strip() if requirement_memo else ""  # 空文字列をデフォルトに
        }
        
        # job_descriptionカラムが必要な場合は追加
        if job_description:
            new_requirement["job_description"] = job_description.strip()
        
        response = db.table('job_requirements').insert(new_requirement).execute()
        
        # Supabaseクライアントのエラーをチェック
        if hasattr(response, 'error') and response.error:
            raise Exception(f"Supabase error: {response.error}")
        
        # response.dataが空の場合、挿入失敗と判断
        if not response.data:
            raise Exception("Failed to insert data into Supabase - empty response data")
        
        requirement_id = response.data[0]['id']
        return RedirectResponse(
            url=f"/admin/requirements/{requirement_id}/view?success=created",
            status_code=303
        )
    except json.JSONDecodeError as e:
        return RedirectResponse(
            url=f"/admin/requirements/new?error=invalid_json&message={e}",
            status_code=303
        )
    except ValueError as e:
        return RedirectResponse(
            url=f"/admin/requirements/new?error=validation_failed&message={e}",
            status_code=303
        )
    except Exception as e:
        import traceback
        
        # URLセーフなエラーメッセージを作成
        import urllib.parse
        error_msg = urllib.parse.quote(str(e))
        
        return RedirectResponse(
            url=f"/admin/requirements/new?error=creation_failed&message={error_msg}",
            status_code=303
        )

@router.get("/admin/requirements/{requirement_id}/view", response_class=HTMLResponse)
async def view_requirement(
    request: Request,
    requirement_id: str,
    user=Depends(get_current_admin_user),
    db=Depends(get_db)
):
    """採用要件詳細ページ"""
    try:
        req_response = db.table('job_requirements').select('*, clients(name)').eq('id', requirement_id).single().execute()
        # req_response.error のチェックを削除
        if not req_response.data:
            raise HTTPException(status_code=404, detail="Requirement not found")
        requirement = req_response.data
        requirement['client_name'] = requirement['clients']['name'] if requirement.get('clients') else 'N/A'

        # structured_dataを日本語で表示できるように整形
        if isinstance(requirement.get('structured_data'), dict):
            requirement['structured_data_formatted'] = json.dumps(
                requirement['structured_data'], indent=2, ensure_ascii=False
            )
        else:
            requirement['structured_data_formatted'] = '{}'
    except Exception as e:
        raise HTTPException(status_code=404, detail="Requirement not found")

    success = request.query_params.get("success")
    
    return templates.TemplateResponse("admin/requirement_detail.html", {
        "request": request,
        "current_user": user,
        "requirement": requirement,
        "success": success,
        "page": "requirements"
    })

@router.get("/admin/requirements/{requirement_id}/edit", response_class=HTMLResponse)
async def edit_requirement(
    request: Request,
    requirement_id: str,
    user=Depends(get_current_admin_user),
    db=Depends(get_db)
):
    """採用要件編集ページ"""
    try:
        # 採用要件を取得
        req_response = db.table('job_requirements').select('*').eq('id', requirement_id).execute()
        if not req_response.data or len(req_response.data) == 0:
            raise HTTPException(status_code=404, detail="Requirement not found")
        requirement = req_response.data[0]

        # descriptionを求人票とメモに分割
        description_text = requirement.get('description', '')
        parts = description_text.split('【求人メモ】')
        job_description = parts[0].replace('【求人票】\n', '').strip()
        requirement_memo = parts[1].strip() if len(parts) > 1 else ''
        requirement['job_description_parsed'] = job_description
        requirement['requirement_memo_parsed'] = requirement_memo

        # 常に日本語で表示するために、ここでJSON文字列に変換しておく
        if isinstance(requirement.get('structured_data'), dict):
            requirement['structured_data_formatted'] = json.dumps(
                requirement['structured_data'], indent=2, ensure_ascii=False
            )
        else:
            requirement['structured_data_formatted'] = '{}'

        # クライアント一覧を取得
        clients_response = db.table('clients').select('id, name').eq('is_active', True).order('name').execute()
        clients = clients_response.data if clients_response.data else []

        return templates.TemplateResponse("admin/requirements_edit.html", {
            "request": request,
            "current_user": user,
            "requirement": requirement,
            "clients": clients,
            "page": "requirements"
        })

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in edit_requirement: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/admin/requirements/{requirement_id}/update")
async def update_requirement(
    request: Request,
    requirement_id: str,
    client_id: str = Form(...),
    title: str = Form(...),
    job_description: str = Form(...),
    requirement_memo: str = Form(...),
    structured_data: str = Form(...),
    is_active: Optional[bool] = Form(False),
    user=Depends(get_current_admin_user),
    db=Depends(get_db)
):
    """採用要件を更新"""
    try:
        # structured_dataのパース
        if not structured_data.strip():
            parsed_structured_data = {}
        else:
            try:
                parsed_structured_data = json.loads(structured_data)
            except json.JSONDecodeError as e:
                return RedirectResponse(
                    url=f"/admin/requirements/{requirement_id}/edit?error=invalid_json",
                    status_code=303
                )
        
        update_data = {
            "client_id": client_id,
            "title": title,
            "description": f"【求人票】\n{job_description}\n\n【求人メモ】\n{requirement_memo}",
            "structured_data": parsed_structured_data,
            "is_active": is_active,
            "updated_at": datetime.now().isoformat(),
            "job_description": job_description.strip(),
            "memo": requirement_memo.strip()
        }
        
        response = db.table('job_requirements').update(update_data).eq('id', requirement_id).execute()
        
        if not response.data:
            raise Exception("Failed to update requirement")

        return RedirectResponse(url=f"/admin/requirements/{requirement_id}/view?success=updated", status_code=303)
    except Exception as e:
        print(f"Error updating requirement: {e}")
        return RedirectResponse(url=f"/admin/requirements/{requirement_id}/edit?error=update_failed", status_code=303)

@router.post("/admin/requirements/{requirement_id}/delete")
async def delete_requirement(
    requirement_id: str,
    user=Depends(get_current_admin_user),
    db=Depends(get_db)
):
    """採用要件を削除"""
    try:
        # まず削除対象が存在するか確認
        check_response = db.table('job_requirements').select('id').eq('id', requirement_id).execute()
        if not check_response.data:
            return RedirectResponse(url="/admin/requirements?error=not_found", status_code=303)
        
        # 削除実行
        response = db.table('job_requirements').delete().eq('id', requirement_id).execute()
        
        # 削除結果の確認
        if not response.data:
            raise Exception("削除に失敗しました")
            
    except Exception as e:
        error_msg = str(e)
        if "violates foreign key constraint" in error_msg:
            # 外部キー制約エラー
            return RedirectResponse(url="/admin/requirements?error=has_related_data", status_code=303)
        else:
            # その他のエラー
            print(f"Error deleting requirement: {error_msg}")
            return RedirectResponse(url="/admin/requirements?error=delete_failed", status_code=303)

    return RedirectResponse(
        url="/admin/requirements?success=deleted",
        status_code=303
    )

@router.post("/api/requirements/structure")
async def structure_requirement(request: Request, user=Depends(get_current_admin_user)):
    """AIを用いて採用要件を構造化する"""
    try:
        from core.services.requirement_structuring_service import RequirementStructuringService

        body = await request.json()
        job_description = body.get('job_description', '')
        job_memo = body.get('job_memo', '')

        if not job_description or not job_memo:
            raise HTTPException(status_code=400, detail="求人票と求人メモの両方が必要です")

        service = RequirementStructuringService()
        structured_data = await service.structure_requirement(job_description, job_memo)

        return JSONResponse(content={
            "success": True,
            "structured_data": structured_data
        })

    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"success": False, "error": e.detail})
    except Exception as e:
        print(f"Error in structure_requirement: {e}")
        return JSONResponse(status_code=500, content={"success": False, "error": "構造化中にサーバーエラーが発生しました"})