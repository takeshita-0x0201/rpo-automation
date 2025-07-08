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
    return []

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