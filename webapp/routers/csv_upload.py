"""
CSVアップロードとPineconeへのベクトル化機能
"""

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks, Request
from fastapi.responses import JSONResponse, StreamingResponse, HTMLResponse
from typing import Optional
import pandas as pd
import json
import os
import sys
import io
from datetime import datetime
import uuid

# ai_matching_systemをインポートパスに追加
sys.path.append(os.path.join(os.path.dirname(__file__), "../../ai_matching_system"))

from .auth import get_current_user_from_cookie

# ai_matching_systemのスクリプトをインポート（後で実装）
# from scripts.enrich_historical_data import process_historical_data  
# from scripts.vectorize_historical_data import HistoricalDataVectorizer

router = APIRouter()

# 管理者またはマネージャーの権限チェック
async def get_current_manager_or_admin_user(user: Optional[dict] = Depends(get_current_user_from_cookie)) -> dict:
    if not user or user.get("role") not in ["manager", "admin"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    return user

# CSVアップロードページ
@router.get("/admin/csv-upload", response_class=HTMLResponse)
async def csv_upload_page(
    request: Request,
    user: Optional[dict] = Depends(get_current_user_from_cookie)
):
    """CSV一括アップロードページ"""
    from fastapi.templating import Jinja2Templates
    from fastapi.responses import RedirectResponse
    import pathlib
    
    # 権限チェック
    if not user or user.get("role") not in ["manager", "admin"]:
        return RedirectResponse(url="/login?error=Unauthorized", status_code=303)
    
    base_dir = pathlib.Path(__file__).parent.parent
    templates = Jinja2Templates(directory=str(base_dir / "templates"))
    
    return templates.TemplateResponse("admin/csv_upload.html", {
        "request": request,
        "current_user": user,
        "user_role": user.get("role")
    })

# アップロード進捗を管理する辞書（本番環境ではRedisを推奨）
upload_progress = {}

@router.post("/api/csv/upload/evaluation-history")
async def upload_evaluation_history(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user: dict = Depends(get_current_manager_or_admin_user)
):
    """評価履歴CSVをアップロードしてPineconeにベクトル化"""
    
    # ファイル検証
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="CSVファイルのみアップロード可能です")
    
    # ファイルサイズ制限（10MB）
    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="ファイルサイズは10MB以下にしてください")
    
    # CSVとして読み込み
    try:
        df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"CSV読み込みエラー: {str(e)}")
    
    # 必須カラムのチェック
    required_columns = ['id', 'resumeText', 'management_number', 'client_evaluation']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise HTTPException(
            status_code=400, 
            detail=f"必須カラムが不足しています: {', '.join(missing_columns)}"
        )
    
    # アップロードIDを生成
    upload_id = str(uuid.uuid4())
    upload_progress[upload_id] = {
        "status": "processing",
        "stage": "準備中",
        "progress": 0,
        "total_records": len(df),
        "processed_records": 0,
        "errors": [],
        "started_at": datetime.now().isoformat()
    }
    
    # バックグラウンドで処理
    background_tasks.add_task(
        process_csv_upload,
        upload_id,
        df,
        user.get("email")
    )
    
    return {
        "upload_id": upload_id,
        "message": "アップロードを開始しました",
        "total_records": len(df)
    }

async def process_csv_upload(upload_id: str, df: pd.DataFrame, username: str):
    """CSVアップロードのバックグラウンド処理"""
    
    try:
        # ステージ1: AIエンリッチメント
        upload_progress[upload_id]["stage"] = "AIエンリッチメント実行中"
        upload_progress[upload_id]["progress"] = 10
        
        # 求人情報（デモ用に固定値、実際には動的に取得）
        import tempfile
        temp_dir = tempfile.gettempdir()
        job_info = {
            "job_description_path": os.path.join(temp_dir, "job_description.txt"),
            "job_memo_path": os.path.join(temp_dir, "job_memo.txt")
        }
        
        # エンリッチメント実行
        enriched_results = []
        batch_size = 5
        
        for i in range(0, len(df), batch_size):
            batch = df.iloc[i:i+batch_size]
            batch_results = await process_batch(batch, job_info)
            enriched_results.extend(batch_results)
            
            # 進捗更新
            processed = i + len(batch)
            upload_progress[upload_id]["processed_records"] = processed
            upload_progress[upload_id]["progress"] = 10 + int((processed / len(df)) * 40)
        
        # ステージ2: ベクトル化とPineconeアップロード
        upload_progress[upload_id]["stage"] = "Pineconeへのアップロード中"
        upload_progress[upload_id]["progress"] = 50
        
        # APIキー取得
        gemini_api_key = os.getenv('GEMINI_API_KEY')
        pinecone_api_key = os.getenv('PINECONE_API_KEY')
        
        if not pinecone_api_key:
            raise Exception("PINECONE_API_KEYが設定されていません")
        
        # ベクトル化実行
        vectorizer = HistoricalDataVectorizer(gemini_api_key, pinecone_api_key)
        vector_results = await vectorizer.process_data(enriched_results, job_info)
        
        # 完了
        upload_progress[upload_id]["status"] = "completed"
        upload_progress[upload_id]["stage"] = "完了"
        upload_progress[upload_id]["progress"] = 100
        upload_progress[upload_id]["completed_at"] = datetime.now().isoformat()
        upload_progress[upload_id]["vector_count"] = vector_results["total_vectors"]
        
    except Exception as e:
        upload_progress[upload_id]["status"] = "failed"
        upload_progress[upload_id]["stage"] = "エラー"
        upload_progress[upload_id]["errors"].append(str(e))

@router.get("/api/csv/upload/{upload_id}/progress")
async def get_upload_progress(
    upload_id: str,
    user: dict = Depends(get_current_user_from_cookie)
):
    """アップロード進捗を取得"""
    
    if upload_id not in upload_progress:
        raise HTTPException(status_code=404, detail="アップロードIDが見つかりません")
    
    return upload_progress[upload_id]

@router.get("/api/csv/template/evaluation-history")
async def download_template(
    user: dict = Depends(get_current_user_from_cookie)
):
    """評価履歴CSVのテンプレートをダウンロード"""
    
    template_data = {
        "id": ["001", "002", "003"],
        "resumeText": [
            "10年間のソフトウェア開発経験...",
            "プロジェクトマネージャーとして5年...",
            "データサイエンティストとして..."
        ],
        "management_number": ["MGT001", "MGT002", "MGT003"],
        "client_evaluation": ["A", "B", "C"],
        "client_comment": [
            "技術力が高く即戦力として期待",
            "経験は十分だが特定分野の知識が不足",
            "ポテンシャルはあるが経験不足"
        ]
    }
    
    df = pd.DataFrame(template_data)
    
    # CSVをメモリ上で作成
    output = io.StringIO()
    df.to_csv(output, index=False, encoding='utf-8-sig')
    output.seek(0)
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=evaluation_history_template.csv"
        }
    )

async def process_batch(batch: pd.DataFrame, job_info: dict) -> list:
    """バッチ処理（実際の実装は既存のenrich_historical_dataの関数を使用）"""
    # ここは実際の実装に合わせて調整
    results = []
    for _, row in batch.iterrows():
        # 仮の処理結果
        result = {
            "id": row["id"],
            "ai_evaluation": {
                "recommendation": "B",
                "score": 75,
                "confidence": "中",
                "reasoning": "技術経験は十分",
                "strengths": ["技術力", "経験"],
                "concerns": ["特定分野の知識"]
            },
            "client_evaluation": row["client_evaluation"],
            "evaluation_match": False
        }
        results.append(result)
    return results