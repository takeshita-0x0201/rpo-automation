"""
CSV アップロード/ダウンロード API
"""
import io
import csv
from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Response, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import pandas as pd

from core.utils.supabase_client import get_supabase_client
from .auth import get_current_user, get_current_user_from_cookie

router = APIRouter(prefix="/api/csv", tags=["csv"])


class UploadResult(BaseModel):
    """アップロード結果"""
    total: int
    success: int
    errors: int
    error_details: List[Dict[str, Any]] = []


@router.post("/upload", response_model=UploadResult)
async def upload_csv(
    file: UploadFile = File(...),
    type: str = None,
    current_user: dict = Depends(get_current_user)
):
    """CSVファイルのアップロード"""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="CSVファイルをアップロードしてください")
    
    if type not in ["candidates", "jobs", "evaluations", "client-evaluations"]:
        raise HTTPException(status_code=400, detail="無効なアップロードタイプです")
    
    # ファイル内容を読み込む
    content = await file.read()
    
    try:
        # pandas DataFrameとして読み込む
        df = pd.read_csv(io.StringIO(content.decode('utf-8')))
        
        # タイプに応じて処理を分岐
        if type == "candidates":
            result = await process_candidates_csv(df, current_user["id"])
        elif type == "jobs":
            result = await process_jobs_csv(df, current_user["id"])
        elif type == "evaluations":
            result = await process_evaluations_csv(df, current_user["id"])
        else:  # client-evaluations
            result = await process_client_evaluations_csv(df, current_user["id"])
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"CSVファイルの処理中にエラーが発生しました: {str(e)}")


async def process_candidates_csv(df: pd.DataFrame, user_id: str) -> UploadResult:
    """候補者CSVの処理"""
    supabase = get_supabase_client()
    result = UploadResult(total=len(df), success=0, errors=0)
    
    # 必須カラムの確認
    required_columns = ["candidate_id", "candidate_name", "candidate_company"]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise HTTPException(
            status_code=400,
            detail=f"必須カラムが不足しています: {', '.join(missing_columns)}"
        )
    
    # 各行を処理
    for index, row in df.iterrows():
        try:
            # データの準備
            candidate_data = {
                "candidate_id": str(row["candidate_id"]),
                "candidate_name": str(row["candidate_name"]),
                "candidate_company": str(row.get("candidate_company", "")),
                "candidate_position": str(row.get("candidate_position", "")),
                "years_of_experience": int(row.get("years_of_experience", 0)) if pd.notna(row.get("years_of_experience")) else None,
                "age": int(row.get("age", 0)) if pd.notna(row.get("age")) else None,
                "annual_income": int(row.get("annual_income", 0)) if pd.notna(row.get("annual_income")) else None,
                "education": str(row.get("education", "")),
                "resume_text": str(row.get("resume_text", "")),
                "created_by": user_id,
                "created_at": datetime.utcnow().isoformat()
            }
            
            # データベースに挿入（重複時は更新）
            response = supabase.table("candidates").upsert(
                candidate_data,
                on_conflict="candidate_id"
            ).execute()
            
            result.success += 1
            
        except Exception as e:
            result.errors += 1
            result.error_details.append({
                "row": index + 2,  # ヘッダー行を考慮
                "message": str(e)
            })
    
    return result


async def process_jobs_csv(df: pd.DataFrame, user_id: str) -> UploadResult:
    """求人CSVの処理"""
    supabase = get_supabase_client()
    result = UploadResult(total=len(df), success=0, errors=0)
    
    # 必須カラムの確認
    required_columns = ["title", "client_name"]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise HTTPException(
            status_code=400,
            detail=f"必須カラムが不足しています: {', '.join(missing_columns)}"
        )
    
    # 各行を処理
    for index, row in df.iterrows():
        try:
            # クライアントの取得または作成
            client_response = supabase.table("clients").select("*").eq(
                "name", str(row["client_name"])
            ).execute()
            
            if client_response.data:
                client_id = client_response.data[0]["id"]
            else:
                # 新規クライアント作成
                new_client = supabase.table("clients").insert({
                    "name": str(row["client_name"]),
                    "industry": str(row.get("client_industry", "")),
                    "created_by": user_id
                }).execute()
                client_id = new_client.data[0]["id"]
            
            # 求人データの準備
            job_data = {
                "title": str(row["title"]),
                "client_id": client_id,
                "department": str(row.get("department", "")),
                "job_type": str(row.get("job_type", "")),
                "employment_type": str(row.get("employment_type", "正社員")),
                "location": str(row.get("location", "")),
                "min_salary": int(row.get("min_salary", 0)) if pd.notna(row.get("min_salary")) else None,
                "max_salary": int(row.get("max_salary", 0)) if pd.notna(row.get("max_salary")) else None,
                "description": str(row.get("description", "")),
                "memo": str(row.get("memo", "")),
                "status": str(row.get("status", "active")),
                "created_by": user_id,
                "created_at": datetime.utcnow().isoformat()
            }
            
            # データベースに挿入
            response = supabase.table("requirements").insert(job_data).execute()
            result.success += 1
            
        except Exception as e:
            result.errors += 1
            result.error_details.append({
                "row": index + 2,
                "message": str(e)
            })
    
    return result


async def process_evaluations_csv(df: pd.DataFrame, user_id: str) -> UploadResult:
    """評価結果CSVの処理"""
    supabase = get_supabase_client()
    result = UploadResult(total=len(df), success=0, errors=0)
    
    # 必須カラムの確認
    required_columns = ["candidate_id", "requirement_id", "score"]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise HTTPException(
            status_code=400,
            detail=f"必須カラムが不足しています: {', '.join(missing_columns)}"
        )
    
    # 各行を処理
    for index, row in df.iterrows():
        try:
            # 評価データの準備
            eval_data = {
                "candidate_id": str(row["candidate_id"]),
                "requirement_id": str(row["requirement_id"]),
                "score": int(row["score"]),
                "recommendation": str(row.get("recommendation", "C")),
                "strengths": row.get("strengths", "").split(";") if pd.notna(row.get("strengths")) else [],
                "concerns": row.get("concerns", "").split(";") if pd.notna(row.get("concerns")) else [],
                "overall_assessment": str(row.get("overall_assessment", "")),
                "evaluated_by": user_id,
                "evaluated_at": datetime.utcnow().isoformat()
            }
            
            # データベースに挿入
            response = supabase.table("ai_evaluations").insert(eval_data).execute()
            result.success += 1
            
        except Exception as e:
            result.errors += 1
            result.error_details.append({
                "row": index + 2,
                "message": str(e)
            })
    
    return result


async def process_client_evaluations_csv(df: pd.DataFrame, user_id: str) -> UploadResult:
    """クライアント評価CSVの処理"""
    supabase = get_supabase_client()
    result = UploadResult(total=len(df), success=0, errors=0)
    
    # 必須カラムの確認
    required_columns = ["candidate_id", "requirement_id", "client_evaluation"]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise HTTPException(
            status_code=400,
            detail=f"必須カラムが不足しています: {', '.join(missing_columns)}"
        )
    
    # 各行を処理
    for index, row in df.iterrows():
        try:
            # 評価データの準備
            eval_data = {
                "candidate_id": str(row["candidate_id"]),
                "requirement_id": str(row["requirement_id"]),
                "client_evaluation": str(row["client_evaluation"]).upper(),
                "client_feedback": str(row.get("client_feedback", "")),
                "evaluation_date": str(row.get("evaluation_date", datetime.utcnow().date())),
                "created_by": user_id,
                "created_at": datetime.utcnow().isoformat()
            }
            
            # client_evaluationsテーブルに挿入（重複時は更新）
            response = supabase.table("client_evaluations").upsert(
                eval_data,
                on_conflict="candidate_id,requirement_id"
            ).execute()
            
            result.success += 1
            
        except Exception as e:
            result.errors += 1
            result.error_details.append({
                "row": index + 2,  # ヘッダー行を考慮
                "message": str(e)
            })
    
    return result


@router.get("/template/{type}")
async def download_template(
    type: str,
    request: Request,
    current_user: Optional[dict] = Depends(get_current_user_from_cookie)
):
    """CSVテンプレートのダウンロード"""
    # Cookieベースの認証チェック
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if type not in ["candidates", "jobs", "evaluations", "client-evaluations"]:
        raise HTTPException(status_code=400, detail="無効なテンプレートタイプです")
    
    # テンプレートデータの定義
    templates = {
        "candidates": {
            "filename": "candidates_template.csv",
            "headers": [
                "candidate_id", "candidate_name", "candidate_company", 
                "candidate_position", "years_of_experience", "age",
                "annual_income", "education", "resume_text"
            ],
            "sample": [
                "C001", "山田太郎", "株式会社ABC", 
                "マネージャー", "10", "35",
                "8000000", "大学卒", "これまでの経歴..."
            ]
        },
        "jobs": {
            "filename": "jobs_template.csv",
            "headers": [
                "title", "client_name", "client_industry", "department",
                "job_type", "employment_type", "location",
                "min_salary", "max_salary", "description", "memo"
            ],
            "sample": [
                "プロジェクトマネージャー", "株式会社XYZ", "IT", "開発部",
                "エンジニア", "正社員", "東京都",
                "6000000", "10000000", "プロジェクト管理業務...", "備考..."
            ]
        },
        "evaluations": {
            "filename": "evaluations_template.csv",
            "headers": [
                "candidate_id", "requirement_id", "score",
                "recommendation", "strengths", "concerns", "overall_assessment"
            ],
            "sample": [
                "C001", "req_001", "85",
                "A", "技術力が高い;リーダーシップがある", "転職回数が多い", "総合的に優秀な候補者です"
            ]
        },
        "client-evaluations": {
            "filename": "client_evaluations_template.csv",
            "headers": [
                "candidate_id", "requirement_id", "client_evaluation",
                "client_feedback", "evaluation_date"
            ],
            "sample": [
                "C001", "req_001", "A",
                "技術力が高く、即戦力として期待できる", "2024-01-15"
            ],
            "additional_rows": [
                ["C001", "req_002", "B", "経験は十分だが、特定技術の知識が不足", "2024-01-16"],
                ["C002", "req_001", "C", "ポテンシャルはあるが経験不足", "2024-01-15"],
                ["C003", "req_003", "D", "求める要件との乖離が大きい", "2024-01-17"],
                ["# 備考: candidate_idとrequirement_idは既存のIDを使用してください", "", "", "", ""],
                ["# 備考: client_evaluationはA/B/C/Dのいずれかを入力してください", "", "", "", ""],
                ["# 備考: evaluation_dateはYYYY-MM-DD形式で入力してください", "", "", "", ""]
            ]
        }
    }
    
    template = templates[type]
    
    # CSVデータを作成
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(template["headers"])
    writer.writerow(template["sample"])
    
    # 追加の行がある場合は書き込む
    if "additional_rows" in template:
        for row in template["additional_rows"]:
            writer.writerow(row)
    
    # ストリーミングレスポンスとして返す
    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),  # BOM付きUTF-8
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={template['filename']}"
        }
    )


@router.get("/export/{type}")
async def export_data(
    type: str,
    current_user: dict = Depends(get_current_user)
):
    """データのCSVエクスポート"""
    if type not in ["candidates", "jobs", "evaluations"]:
        raise HTTPException(status_code=400, detail="無効なエクスポートタイプです")
    
    supabase = get_supabase_client()
    
    # データの取得
    if type == "candidates":
        response = supabase.table("candidates").select("*").execute()
        data = response.data
        
        # DataFrameに変換
        df = pd.DataFrame(data)
        if not df.empty:
            # カラムの順序を整理
            columns_order = [
                "candidate_id", "candidate_name", "candidate_company",
                "candidate_position", "years_of_experience", "age",
                "annual_income", "education", "resume_text"
            ]
            df = df[[col for col in columns_order if col in df.columns]]
    
    elif type == "jobs":
        response = supabase.table("requirements").select(
            "*, client:clients(name, industry)"
        ).execute()
        data = response.data
        
        # DataFrameに変換して整形
        df = pd.DataFrame(data)
        if not df.empty:
            df["client_name"] = df["client"].apply(lambda x: x["name"] if x else "")
            df["client_industry"] = df["client"].apply(lambda x: x.get("industry", "") if x else "")
            
            columns_order = [
                "title", "client_name", "client_industry", "department",
                "job_type", "employment_type", "location",
                "min_salary", "max_salary", "description", "memo", "status"
            ]
            df = df[[col for col in columns_order if col in df.columns]]
    
    else:  # evaluations
        response = supabase.table("ai_evaluations").select("*").execute()
        data = response.data
        
        df = pd.DataFrame(data)
        if not df.empty:
            # リストを文字列に変換
            df["strengths"] = df["strengths"].apply(lambda x: ";".join(x) if x else "")
            df["concerns"] = df["concerns"].apply(lambda x: ";".join(x) if x else "")
            
            columns_order = [
                "candidate_id", "requirement_id", "score",
                "recommendation", "strengths", "concerns", "overall_assessment"
            ]
            df = df[[col for col in columns_order if col in df.columns]]
    
    # CSVに変換
    output = io.StringIO()
    df.to_csv(output, index=False, encoding='utf-8-sig')
    output.seek(0)
    
    # ファイル名を生成
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{type}_export_{timestamp}.csv"
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )