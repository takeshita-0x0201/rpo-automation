import pathlib
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
import uuid
from datetime import datetime
import json # 追加
from .auth import get_current_user_from_cookie

async def get_current_admin_user(user: dict = Depends(get_current_user_from_cookie)) -> dict:
    print(f"get_current_admin_user received user: {user}") # デバッグログ追加
    if not user or user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    return user
from ...utils.supabase_client import get_supabase_client as get_db

router = APIRouter()
templates_path = pathlib.Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_path))

@router.get("/admin/requirements", response_class=HTMLResponse)
async def requirements_list(request: Request, user=Depends(get_current_admin_user), db=Depends(get_db)):
    """採用要件一覧ページ"""
    try:
        # 1. クライアント一覧を取得
        print("Fetching clients from Supabase...")
        clients_response = db.table('clients').select('id, name').execute()
        print(f"Supabase clients_response in requirements_list: {clients_response}")
        if not clients_response.data:
            print("No client data found.")
            clients_map = {}
        else:
            clients_map = {str(client['id']): client['name'] for client in clients_response.data}

        # 2. 採用要件一覧を取得
        print("Fetching job_requirements from Supabase...")
        req_response = db.table('job_requirements').select('*').order('created_at', desc=True).execute()
        print(f"Supabase req_response in requirements_list: {req_response}")
        
        if not req_response.data:
            print("No job_requirements data found.")
            requirements = []
        else:
            requirements = req_response.data
            
            # 3. Pythonでクライアント名を紐付け
            for req in requirements:
                req['client_name'] = clients_map.get(str(req['client_id']), 'N/A')

    except Exception as e:
        requirements = []
        print(f"Error fetching requirements in requirements_list: {e}")

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
        print(f"Supabase clients_response: {clients_response}") # デバッグログ追加
        clients = clients_response.data
    except Exception as e:
        clients = []
        print(f"Error fetching clients in requirements_new: {e}") # デバッグログ追加

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
    title: str = Form(...),
    requirement_text: str = Form(...),
    structured_data: str = Form(...),
    user=Depends(get_current_admin_user),
    db=Depends(get_db)
):
    """採用要件を作成"""
    print("create_requirement function called.") # 関数呼び出しの確認ログ
    try:
        # structured_dataが空文字列の場合のハンドリング
        if not structured_data.strip():
            raise ValueError("構造化データが空です。AIで構造化を実行してください。")

        parsed_structured_data = json.loads(structured_data) # JSON文字列をPython辞書に変換
        print(f"Parsed structured_data: {parsed_structured_data}") # パース後のデータを確認

        new_requirement = {
            "client_id": client_id,
            "title": title,
            "description": requirement_text,
            "structured_data": parsed_structured_data,
            "created_by": user['id']
        }
        print(f"Attempting to insert new requirement: {new_requirement}") # デバッグログ追加
        response = db.table('job_requirements').insert(new_requirement).execute()
        print(f"Supabase insert response: {response}") # デバッグログ追加
        
        # response.dataが空の場合、挿入失敗と判断
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to insert data into Supabase.")
        
        requirement_id = response.data[0]['id']
        return RedirectResponse(
            url=f"/admin/requirements/{requirement_id}/view?success=created",
            status_code=303
        )
    except json.JSONDecodeError as e:
        print(f"JSONDecodeError in create_requirement: {e}")
        return RedirectResponse(
            url=f"/admin/requirements/new?error=invalid_json&message={e}",
            status_code=303
        )
    except ValueError as e:
        print(f"ValueError in create_requirement: {e}")
        return RedirectResponse(
            url=f"/admin/requirements/new?error=validation_failed&message={e}",
            status_code=303
        )
    except Exception as e:
        print(f"Error creating requirement: {e}") # デバッグログ追加
        return RedirectResponse(
            url="/admin/requirements/new?error=creation_failed",
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
    except Exception as e:
        print(f"Error in view_requirement: {e}") # デバッグログ追加
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

@router.post("/admin/requirements/{requirement_id}/update")
async def update_requirement(
    request: Request,
    requirement_id: str,
    client_id: str = Form(...),
    title: str = Form(...),
    requirement_text: str = Form(...),
    structured_data: str = Form(...),
    is_active: Optional[bool] = Form(False),
    user=Depends(get_current_admin_user),
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

        return RedirectResponse(url=f"/admin/requirements/{requirement_id}/view?success=updated", status_code=303)
    except Exception as e:
        return RedirectResponse(url=f"/admin/requirements/{requirement_id}/edit?error=update_failed", status_code=303)

@router.post("/admin/requirements/{requirement_id}/delete")
async def delete_requirement(
    requirement_id: str,
    user=Depends(get_current_admin_user),
    db=Depends(get_db)
):
    """採用要件を削除"""
    try:
        response = db.table('job_requirements').delete().eq('id', requirement_id).execute()
        if response.error:
            raise HTTPException(status_code=500, detail=str(response.error))
    except Exception as e:
        return RedirectResponse(url=f"/admin/requirements?error=delete_failed", status_code=303)

    return RedirectResponse(
        url="/admin/requirements?success=deleted",
        status_code=303
    )