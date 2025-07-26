from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from typing import List, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)
from datetime import datetime
from pydantic import BaseModel
from uuid import UUID
import json
from core.ai.gemini_client import GeminiClient

def parse_iso_datetime(date_string: str) -> datetime:
    """ISO形式の日付文字列を安全にパースする（全Pythonバージョン対応）"""
    if not date_string:
        return datetime.now()
    
    try:
        # オリジナルの文字列を保存
        original_string = date_string
        
        # Zを+00:00に置き換え
        date_string = date_string.replace('Z', '+00:00')
        
        # まず、Python 3.7+のfromisoformatを試す（存在する場合）
        if hasattr(datetime, 'fromisoformat'):
            try:
                # マイクロ秒が6桁を超える場合は切り詰める
                if '.' in date_string:
                    base, microseconds_and_tz = date_string.split('.', 1)
                    # タイムゾーン部分を分離
                    if '+' in microseconds_and_tz:
                        microseconds, tz = microseconds_and_tz.split('+', 1)
                        tz = '+' + tz
                    elif '-' in microseconds_and_tz and len(microseconds_and_tz) > 6:
                        # タイムゾーンの'-'を探す（マイクロ秒部分の後）
                        for i in range(6, len(microseconds_and_tz)):
                            if microseconds_and_tz[i] == '-':
                                microseconds = microseconds_and_tz[:i]
                                tz = microseconds_and_tz[i:]
                                break
                        else:
                            microseconds = microseconds_and_tz
                            tz = ''
                    else:
                        microseconds = microseconds_and_tz
                        tz = ''
                    
                    # マイクロ秒を6桁に調整
                    microseconds = microseconds[:6].ljust(6, '0')
                    date_string = f"{base}.{microseconds}{tz}"
                
                return datetime.fromisoformat(date_string)
            except Exception:
                pass
        
        # Python 3.6以前またはfromisoformatが失敗した場合
        # タイムゾーン情報とマイクロ秒を手動で処理
        date_string = original_string.replace('Z', '')
        
        # タイムゾーンオフセットを抽出
        tz_offset = None
        if '+' in date_string[-6:] or (date_string.count('-') > 2 and '-' in date_string[-6:]):
            # タイムゾーンがある場合
            if '+' in date_string[-6:]:
                dt_part, tz_part = date_string.rsplit('+', 1)
                tz_offset = '+' + tz_part
            else:
                # 最後の'-'がタイムゾーンの場合
                parts = date_string.split('-')
                if len(parts[-1]) <= 4 and ':' in parts[-1]:  # タイムゾーンの形式
                    dt_part = '-'.join(parts[:-1])
                    tz_offset = '-' + parts[-1]
                else:
                    dt_part = date_string
            date_string = dt_part
        
        # マイクロ秒を処理
        if '.' in date_string:
            dt_part, microseconds = date_string.split('.', 1)
            # マイクロ秒を6桁に調整
            microseconds = int(microseconds[:6].ljust(6, '0'))
            dt = datetime.strptime(dt_part, '%Y-%m-%dT%H:%M:%S')
            dt = dt.replace(microsecond=microseconds)
        else:
            dt = datetime.strptime(date_string, '%Y-%m-%dT%H:%M:%S')
        
        return dt
        
    except Exception as e:
        logger.warning(f"Failed to parse datetime '{date_string}': {e}")
        # 最終的なフォールバック
        try:
            # 基本的な形式のみを抽出
            basic_format = date_string.split('.')[0].split('+')[0].split('Z')[0]
            if basic_format.count('-') > 2:
                # タイムゾーンの'-'を除去
                parts = basic_format.split('T')
                if len(parts) == 2:
                    date_part = parts[0]
                    time_part = parts[1].split('-')[0]  # タイムゾーンを除去
                    basic_format = f"{date_part}T{time_part}"
            
            return datetime.strptime(basic_format, '%Y-%m-%dT%H:%M:%S')
        except Exception:
            logger.error(f"Unable to parse datetime '{date_string}', using current time")
            return datetime.now()

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
        from core.utils.supabase_client import get_supabase_client
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
                    created_at=parse_iso_datetime(req.get('created_at', '')),
                    updated_at=parse_iso_datetime(req.get('updated_at', ''))
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
        **requirement.model_dump(),
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
    text: Optional[str] = None  # 後方互換性のため残す（オプショナルに変更）
    job_description: Optional[str] = None
    job_memo: Optional[str] = None

class StructureResponse(BaseModel):
    structured_data: Dict[str, Any]
    success: bool
    error: Optional[str] = None

@router.post("/structure", response_model=StructureResponse)
async def structure_requirement(request: StructureRequest):
    """
    採用要件テキストをAIで構造化
    新しい汎用プロンプトテンプレートを使用
    """
    logger.info(f"Structure request received: text={request.text is not None}, job_description={request.job_description is not None}, job_memo={request.job_memo is not None}")
    try:
        # 新しいAPIの場合（job_descriptionとjob_memoが提供される）
        if request.job_description is not None and request.job_memo is not None:
            print("Using new generic structure prompt template...")
            print(f"Job description length: {len(request.job_description)}")
            print(f"Job memo length: {len(request.job_memo)}")
            
            # Gemini clientを初期化
            gemini_client = GeminiClient()
            
            # job_descriptionとjob_memoを結合して構造化
            combined_text = f"求人情報:\n{request.job_description}\n\n求人メモ:\n{request.job_memo}"
            
            # 構造化を実行
            raw_structured_data = await gemini_client.structure_requirement(combined_text)
            
            # MarkdownのJSONコードブロックからJSON文字列を抽出
            import re
            match = re.search(r"```json\n([\s\S]*?)\n```", raw_structured_data)
            if not match:
                raise ValueError("AIからの応答にJSONコードブロックが見つかりませんでした。")
            
            json_string = match.group(1).strip()
            
            if json_string.lower() == "null":
                raise ValueError("AIからの応答がJSONコードブロック内に'null'を含んでいました。")
            
            structured_data = json.loads(json_string)
            
            print(f"Structured data generated successfully")
            
            return StructureResponse(
                structured_data=structured_data,
                success=True
            )
        
        # 既存のAPIの場合（textのみ）- 後方互換性のため
        elif request.text is not None:
            print("Using legacy structure method...")
            raw_structured_data = ""
            
            # Gemini clientを初期化
            gemini_client = GeminiClient()
            
            # 構造化を実行
            raw_structured_data = await gemini_client.structure_requirement(request.text)
            
            # MarkdownのJSONコードブロックからJSON文字列を抽出
            import re
            match = re.search(r"```json\n([\s\S]*?)\n```", raw_structured_data)
            if not match:
                raise ValueError("AIからの応答にJSONコードブロックが見つかりませんでした。")
            
            json_string = match.group(1).strip()
            
            if json_string.lower() == "null":
                raise ValueError("AIからの応答がJSONコードブロック内に'null'を含んでいました。")
            
            structured_data = json.loads(json_string)
            
            if structured_data is None:
                raise ValueError("AIからの応答が空のJSON（null）でした。")
            
            if not isinstance(structured_data, dict):
                raise ValueError(f"AIからの応答が期待する辞書型ではありませんでした: {type(structured_data)}")
            
            return StructureResponse(
                structured_data=structured_data,
                success=True
            )
        
        # どちらの形式でもない場合
        else:
            return StructureResponse(
                structured_data={},
                success=False,
                error="Invalid request: Either provide 'text' for legacy API or both 'job_description' and 'job_memo' for new API"
            )
            
    except json.JSONDecodeError as e:
        print(f"JSONDecodeError: {e}")
        return StructureResponse(
            structured_data={},
            success=False,
            error=f"AIからの応答が不正なJSON形式です: {e}"
        )
    except Exception as e:
        print(f"Error during structure_requirement: {e}")
        import traceback
        traceback.print_exc()
        return StructureResponse(
            structured_data={},
            success=False,
            error=str(e)
        )