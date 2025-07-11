from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel
from uuid import UUID
import json
from ...ai.gemini_client import GeminiClient

router = APIRouter()

class RequirementCreate(BaseModel):
    client_id: str
    title: str
    description: str
    position: str
    required_skills: List[str]
    preferred_skills: Optional[List[str]] = []
    experience_years_min: Optional[int] = 0
    experience_years_max: Optional[int] = None
    education_requirements: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    location: Optional[str] = None
    remote_work: Optional[str] = "not_allowed"
    benefits: Optional[List[str]] = []
    is_active: bool = True

class RequirementResponse(BaseModel):
    id: str
    client_id: str
    title: str
    description: str
    position: str
    required_skills: List[str]
    preferred_skills: List[str]
    experience_years_min: int
    experience_years_max: Optional[int]
    education_requirements: Optional[str]
    salary_min: Optional[int]
    salary_max: Optional[int]
    location: Optional[str]
    remote_work: str
    benefits: List[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

@router.get("/", response_model=List[RequirementResponse])
async def list_requirements(
    client_id: Optional[str] = None,
    is_active: Optional[bool] = True,
    skip: int = 0,
    limit: int = 100
):
    """採用要件一覧を取得"""
    try:
        from ...utils.supabase_client import get_supabase_client
        supabase = get_supabase_client()
        
        # クエリを構築
        query = supabase.table('job_requirements').select('*')
        
        if client_id:
            query = query.eq('client_id', client_id)
        if is_active is not None:
            query = query.eq('is_active', is_active)
            
        # 結果を取得
        response = query.order('created_at', desc=True).range(skip, skip + limit - 1).execute()
        
        if response.data:
            # レスポンス形式に変換
            requirements = []
            for req in response.data:
                requirements.append(RequirementResponse(
                    id=req['id'],
                    client_id=req['client_id'],
                    title=req['title'],
                    description=req.get('description', ''),
                    position=req.get('position', req['title']),  # positionがない場合はtitleを使用
                    required_skills=req.get('structured_data', {}).get('required_skills', []) if req.get('structured_data') else [],
                    preferred_skills=req.get('structured_data', {}).get('preferred_skills', []) if req.get('structured_data') else [],
                    experience_years_min=req.get('structured_data', {}).get('experience_years_min', 0) if req.get('structured_data') else 0,
                    experience_years_max=req.get('structured_data', {}).get('experience_years_max') if req.get('structured_data') else None,
                    education_requirements=req.get('structured_data', {}).get('education_requirements') if req.get('structured_data') else None,
                    salary_min=req.get('structured_data', {}).get('salary_min') if req.get('structured_data') else None,
                    salary_max=req.get('structured_data', {}).get('salary_max') if req.get('structured_data') else None,
                    location=req.get('structured_data', {}).get('location') if req.get('structured_data') else None,
                    remote_work=req.get('structured_data', {}).get('remote_work', 'not_allowed') if req.get('structured_data') else 'not_allowed',
                    benefits=req.get('structured_data', {}).get('benefits', []) if req.get('structured_data') else [],
                    is_active=req.get('is_active', True),
                    created_at=datetime.fromisoformat(req['created_at'].replace('Z', '+00:00')) if req.get('created_at') else datetime.now(),
                    updated_at=datetime.fromisoformat(req['updated_at'].replace('Z', '+00:00')) if req.get('updated_at') else datetime.now()
                ))
            return requirements
        else:
            return []
            
    except Exception as e:
        print(f"Error fetching requirements: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{requirement_id}", response_model=RequirementResponse)
async def get_requirement(requirement_id: str):
    raise HTTPException(status_code=404, detail="Requirement not found")

@router.post("/", response_model=RequirementResponse)
async def create_requirement(requirement: RequirementCreate):
    return RequirementResponse(
        id="dummy-id",
        **requirement.dict(),
        created_at=datetime.now(),
        updated_at=datetime.now()
    )

@router.put("/{requirement_id}", response_model=RequirementResponse)
async def update_requirement(requirement_id: str, requirement: RequirementCreate):
    raise HTTPException(status_code=404, detail="Requirement not found")

@router.delete("/{requirement_id}")
async def delete_requirement(requirement_id: str):
    return {"message": "Requirement deleted successfully"}

@router.post("/{requirement_id}/activate")
async def activate_requirement(requirement_id: str):
    return {"message": "Requirement activated successfully"}

@router.post("/{requirement_id}/deactivate")
async def deactivate_requirement(requirement_id: str):
    return {"message": "Requirement deactivated successfully"}

class StructureRequest(BaseModel):
    text: str

class StructureResponse(BaseModel):
    structured_data: Dict[str, Any]
    success: bool
    error: Optional[str] = None

@router.post("/structure", response_model=StructureResponse)
async def structure_requirement(request: StructureRequest):
    """
    採用要件テキストをAIで構造化
    """
    raw_structured_data = "" # 初期化
    try:
        print("Attempting to initialize GeminiClient...")
        # Gemini clientを初期化
        gemini_client = GeminiClient()
        print("GeminiClient initialized successfully.")
        
        print(f"Structuring text: {request.text[:50]}...") # テキストの冒頭50文字を表示
        # 構造化を実行
        raw_structured_data = await gemini_client.structure_requirement(request.text)
        print(f"Raw structured_data received: {raw_structured_data[:500]}...") # 生の応答をログに出力

        # MarkdownのJSONコードブロックからJSON文字列を抽出
        import re
        match = re.search(r"```json\n([\s\S]*?)\n```", raw_structured_data)
        if not match:
            raise ValueError("AIからの応答にJSONコードブロックが見つかりませんでした。")
        
        json_string = match.group(1).strip()
        print(f"JSON string extracted: '{json_string}'") # デバッグログ追加

        if json_string.lower() == "null":
            raise ValueError("AIからの応答がJSONコードブロック内に'null'を含んでいました。")

        structured_data = json.loads(json_string) # JSON文字列をPython辞書に変換
        print(f"Parsed structured_data: {structured_data}") # デバッグログ追加

        # structured_dataがNoneの場合のハンドリングを追加
        if structured_data is None:
            raise ValueError("AIからの応答が空のJSON（null）でした。")
        
        # structured_dataが辞書型でない場合のハンドリングを追加 (念のため)
        if not isinstance(structured_data, dict):
            raise ValueError(f"AIからの応答が期待する辞書型ではありませんでした: {type(structured_data)}")
        
        return StructureResponse(
            structured_data=structured_data,
            success=True
        )
    except json.JSONDecodeError as e:
        print(f"JSONDecodeError: {e}")
        print(f"Raw structured_data that caused error: {raw_structured_data}")
        return StructureResponse(
            structured_data={},
            success=False,
            error=f"AIからの応答が不正なJSON形式です: {e}"
        )
    except Exception as e:
        print(f"Error during structure_requirement: {e}")
        return StructureResponse(
            structured_data={},
            success=False,
            error=str(e)
        )