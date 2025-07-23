import pathlib
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
import uuid
from datetime import datetime
import json
from .auth import get_current_user_from_cookie

async def get_current_manager_user(user: dict = Depends(get_current_user_from_cookie)) -> dict:
    if not user or user.get("role") != "manager":
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

@router.get("/manager/requirements", response_class=HTMLResponse)
async def requirements_list(request: Request, user=Depends(get_current_manager_user), db=Depends(get_db)):
    """採用要件一覧ページ"""
    try:
        # 1. クライアント一覧を取得
        clients_response = db.table('clients').select('id, name').execute()
        if not clients_response.data:
            clients_map = {}
        else:
            clients_map = {str(client['id']): client['name'] for client in clients_response.data}

        # 2. 採用要件一覧を取得
        req_response = db.table('job_requirements').select('*').order('created_at', desc=True).execute()
        
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

@router.get("/manager/requirements/new", response_class=HTMLResponse)
async def requirements_new(request: Request, user=Depends(get_current_manager_user), db=Depends(get_db)):
    """新規採用要件作成ページ"""
    try:
        # クライアント一覧を取得
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

@router.post("/manager/requirements/create")
async def create_requirement(
    request: Request,
    client_id: str = Form(...),
    position: str = Form(...),
    job_description: str = Form(...),
    requirement_memo: str = Form(...),
    structured_data: str = Form(...),
    user=Depends(get_current_manager_user),
    db=Depends(get_db)
):
    """採用要件を作成"""
    try:
        # requirement_idの連番を生成
        try:
            result = db.rpc('get_next_requirement_id').execute()
            if result.data:
                requirement_id = result.data
            else:
                # フォールバック: 関数が使えない場合
                import uuid
                requirement_id = f"req-temp-{str(uuid.uuid4())[:8]}"
        except Exception as e:
            # フォールバック
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
            url=f"/manager/requirements/{requirement_id}/view?success=created",
            status_code=303
        )
    except json.JSONDecodeError as e:
        return RedirectResponse(
            url=f"/manager/requirements/new?error=invalid_json&message={e}",
            status_code=303
        )
    except ValueError as e:
        return RedirectResponse(
            url=f"/manager/requirements/new?error=validation_failed&message={str(e)}",
            status_code=303
        )
    except Exception as e:
        import traceback
        
        # URLセーフなエラーメッセージを作成
        import urllib.parse
        error_msg = urllib.parse.quote(str(e))
        
        return RedirectResponse(
            url=f"/manager/requirements/new?error=creation_failed&message={error_msg}",
            status_code=303
        )

@router.get("/manager/requirements/{requirement_id}/view", response_class=HTMLResponse)
async def view_requirement(
    request: Request,
    requirement_id: str,
    user=Depends(get_current_manager_user),
    db=Depends(get_db)
):
    """採用要件詳細ページ"""
    try:
        req_response = db.table('job_requirements').select('*, clients(name)').eq('id', requirement_id).single().execute()
        if not req_response.data:
            raise HTTPException(status_code=404, detail="Requirement not found")
        requirement = req_response.data
        requirement['client_name'] = requirement['clients']['name'] if requirement.get('clients') else 'N/A'
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

@router.get("/manager/requirements/{requirement_id}/edit", response_class=HTMLResponse)
async def edit_requirement(
    request: Request,
    requirement_id: str,
    user=Depends(get_current_manager_user),
    db=Depends(get_db)
):
    """採用要件編集ページ"""
    try:
        req_response = db.table('job_requirements').select('*').eq('id', requirement_id).single().execute()
        if req_response.error:
            raise HTTPException(status_code=404, detail="Requirement not found")
        requirement = req_response.data

        clients_response = db.table('clients').select('id, name').eq('is_active', True).execute()
        if clients_response.error:
            raise HTTPException(status_code=500, detail=str(clients_response.error))
        clients = clients_response.data

    except Exception as e:
        raise HTTPException(status_code=404, detail="Requirement not found")

    return templates.TemplateResponse("admin/requirements_edit.html", {
        "request": request,
        "current_user": user,
        "requirement": requirement,
        "clients": clients,
        "page": "requirements"
    })

@router.post("/manager/requirements/{requirement_id}/update")
async def update_requirement(
    request: Request,
    requirement_id: str,
    client_id: str = Form(...),
    title: str = Form(...),
    requirement_text: str = Form(...),
    structured_data: str = Form(...),
    is_active: Optional[bool] = Form(False),
    user=Depends(get_current_manager_user),
    db=Depends(get_db)
):
    """採用要件を更新"""
    try:
        update_data = {
            "client_id": client_id,
            "title": title,
            "description": requirement_text,
            "structured_data": structured_data,
            "is_active": is_active,
            "updated_at": datetime.now().isoformat()
        }
        response = db.table('job_requirements').update(update_data).eq('id', requirement_id).execute()
        if response.error:
            raise HTTPException(status_code=500, detail=str(response.error))

        return RedirectResponse(url=f"/manager/requirements/{requirement_id}/view?success=updated", status_code=303)
    except Exception as e:
        return RedirectResponse(url=f"/manager/requirements/{requirement_id}/edit?error=update_failed", status_code=303)

@router.post("/manager/requirements/{requirement_id}/delete")
async def delete_requirement(
    requirement_id: str,
    user=Depends(get_current_manager_user),
    db=Depends(get_db)
):
    """採用要件を削除"""
    try:
        # まず削除対象が存在するか確認
        check_response = db.table('job_requirements').select('id').eq('id', requirement_id).execute()
        if not check_response.data:
            return RedirectResponse(url="/manager/requirements?error=not_found", status_code=303)
        
        # 削除実行
        response = db.table('job_requirements').delete().eq('id', requirement_id).execute()
        
        # 削除結果の確認
        if not response.data:
            raise Exception("削除に失敗しました")
            
    except Exception as e:
        error_msg = str(e)
        if "violates foreign key constraint" in error_msg:
            # 外部キー制約エラー
            return RedirectResponse(url="/manager/requirements?error=has_related_data", status_code=303)
        else:
            # その他のエラー
            print(f"Error deleting requirement: {error_msg}")
            return RedirectResponse(url="/manager/requirements?error=delete_failed", status_code=303)

    return RedirectResponse(
        url="/manager/requirements?success=deleted",
        status_code=303
    )