import pathlib
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from datetime import datetime
from .auth import get_current_user_from_cookie
from ...utils.supabase_client import get_supabase_client as get_db

async def get_current_manager_user(user: dict = Depends(get_current_user_from_cookie)) -> dict:
    if not user or user.get("role") not in ["manager", "admin"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    return user

router = APIRouter()
templates_path = pathlib.Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_path))

@router.get("/manager/job-postings", response_class=HTMLResponse)
async def job_postings_list(
    request: Request, 
    user=Depends(get_current_manager_user), 
    db=Depends(get_db)
):
    """求人票一覧ページ"""
    try:
        # 求人票一覧を取得
        response = db.table('job_postings').select('*').order('created_at', desc=True).execute()
        job_postings = response.data if response.data else []
        
        # 各求人票に関連する採用要件数を取得
        for posting in job_postings:
            req_count = db.table('job_requirements')\
                .select('id', count='exact')\
                .eq('job_posting_id', posting['id'])\
                .execute()
            posting['requirement_count'] = req_count.count if req_count else 0
            
    except Exception as e:
        print(f"Error fetching job postings: {e}")
        job_postings = []

    return templates.TemplateResponse("admin/job_postings_list.html", {
        "request": request,
        "current_user": user,
        "job_postings": job_postings,
        "page": "job_postings"
    })

@router.get("/manager/job-postings/new", response_class=HTMLResponse)
async def job_postings_new(
    request: Request, 
    user=Depends(get_current_manager_user)
):
    """新規求人票作成ページ"""
    return templates.TemplateResponse("admin/job_postings_new.html", {
        "request": request,
        "current_user": user,
        "page": "job_postings"
    })

@router.post("/manager/job-postings/create")
async def create_job_posting(
    request: Request,
    position: str = Form(...),
    job_description: str = Form(...),
    memo: Optional[str] = Form(None),
    user=Depends(get_current_manager_user),
    db=Depends(get_db)
):
    """求人票を作成"""
    try:
        # 次の連番IDを取得
        result = db.rpc('get_next_job_posting_id').execute()
        if not result.data:
            raise ValueError("Failed to generate job posting ID")
        
        new_id = result.data
        
        # 求人票を作成
        new_posting = {
            "id": new_id,
            "position": position.strip(),
            "job_description": job_description.strip(),
            "memo": memo.strip() if memo else None,
            "created_by": user['id']
        }
        
        response = db.table('job_postings').insert(new_posting).execute()
        
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to create job posting")
        
        posting_id = response.data[0]['id']
        
        return RedirectResponse(
            url=f"/manager/job-postings/{posting_id}/view?success=created",
            status_code=303
        )
        
    except Exception as e:
        print(f"Error creating job posting: {e}")
        return RedirectResponse(
            url="/manager/job-postings/new?error=creation_failed",
            status_code=303
        )

@router.get("/manager/job-postings/{posting_id}/view", response_class=HTMLResponse)
async def view_job_posting(
    request: Request,
    posting_id: str,
    user=Depends(get_current_manager_user),
    db=Depends(get_db)
):
    """求人票詳細ページ"""
    try:
        # 求人票を取得
        posting_response = db.table('job_postings')\
            .select('*, users!created_by(email)')\
            .eq('id', posting_id)\
            .single()\
            .execute()
            
        if not posting_response.data:
            raise HTTPException(status_code=404, detail="Job posting not found")
            
        posting = posting_response.data
        
        # 関連する採用要件を取得
        requirements_response = db.table('job_requirements')\
            .select('*, clients(name)')\
            .eq('job_posting_id', posting_id)\
            .order('created_at', desc=True)\
            .execute()
            
        requirements = requirements_response.data if requirements_response.data else []
        
    except Exception as e:
        print(f"Error viewing job posting: {e}")
        raise HTTPException(status_code=404, detail="Job posting not found")

    success = request.query_params.get("success")
    
    return templates.TemplateResponse("admin/job_posting_detail.html", {
        "request": request,
        "current_user": user,
        "posting": posting,
        "requirements": requirements,
        "success": success,
        "page": "job_postings"
    })

@router.get("/manager/job-postings/{posting_id}/edit", response_class=HTMLResponse)
async def edit_job_posting(
    request: Request,
    posting_id: str,
    user=Depends(get_current_manager_user),
    db=Depends(get_db)
):
    """求人票編集ページ"""
    try:
        response = db.table('job_postings')\
            .select('*')\
            .eq('id', posting_id)\
            .single()\
            .execute()
            
        if not response.data:
            raise HTTPException(status_code=404, detail="Job posting not found")
            
        posting = response.data
        
    except Exception as e:
        raise HTTPException(status_code=404, detail="Job posting not found")

    return templates.TemplateResponse("admin/job_posting_edit.html", {
        "request": request,
        "current_user": user,
        "posting": posting,
        "page": "job_postings"
    })

@router.post("/manager/job-postings/{posting_id}/update")
async def update_job_posting(
    request: Request,
    posting_id: str,
    position: str = Form(...),
    job_description: str = Form(...),
    memo: Optional[str] = Form(None),
    user=Depends(get_current_manager_user),
    db=Depends(get_db)
):
    """求人票を更新"""
    try:
        update_data = {
            "position": position.strip(),
            "job_description": job_description.strip(),
            "memo": memo.strip() if memo else None,
            "updated_at": datetime.now().isoformat()
        }
        
        response = db.table('job_postings')\
            .update(update_data)\
            .eq('id', posting_id)\
            .execute()
            
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to update job posting")

        return RedirectResponse(
            url=f"/manager/job-postings/{posting_id}/view?success=updated", 
            status_code=303
        )
        
    except Exception as e:
        return RedirectResponse(
            url=f"/manager/job-postings/{posting_id}/edit?error=update_failed", 
            status_code=303
        )

@router.post("/manager/job-postings/{posting_id}/delete")
async def delete_job_posting(
    posting_id: str,
    user=Depends(get_current_manager_user),
    db=Depends(get_db)
):
    """求人票を削除"""
    try:
        # 関連する採用要件があるかチェック
        req_check = db.table('job_requirements')\
            .select('id', count='exact')\
            .eq('job_posting_id', posting_id)\
            .execute()
            
        if req_check.count > 0:
            return RedirectResponse(
                url=f"/manager/job-postings/{posting_id}/view?error=has_requirements",
                status_code=303
            )
        
        # 削除実行
        response = db.table('job_postings')\
            .delete()\
            .eq('id', posting_id)\
            .execute()
            
        if response.error:
            raise HTTPException(status_code=500, detail=str(response.error))
            
    except Exception as e:
        return RedirectResponse(
            url=f"/manager/job-postings?error=delete_failed", 
            status_code=303
        )

    return RedirectResponse(
        url="/manager/job-postings?success=deleted",
        status_code=303
    )