"""
Cloud Function: 候補者検索処理
Bizreachから候補者を検索し、AIで評価を行う
"""
import functions_framework
import os
import json
import logging
from datetime import datetime
from google.cloud import bigquery, pubsub_v1
import asyncio
from typing import Dict, List, Any

# ローカルモジュールのインポート
from search_handler import SearchHandler
from ai_evaluator import AIEvaluator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@functions_framework.http
def search_candidates(request):
    """
    HTTPトリガーによる候補者検索
    
    Expected JSON payload:
    {
        "search_id": "uuid",
        "requirement_id": "uuid",
        "search_params": {...},
        "max_candidates": 50
    }
    """
    try:
        # リクエストの検証
        request_json = request.get_json(silent=True)
        if not request_json:
            return {"error": "Invalid request body"}, 400
        
        search_id = request_json.get("search_id")
        requirement_id = request_json.get("requirement_id")
        search_params = request_json.get("search_params", {})
        max_candidates = request_json.get("max_candidates", 50)
        
        if not all([search_id, requirement_id]):
            return {"error": "Missing required fields"}, 400
        
        # 処理時間の制限チェック（9分 = 540秒）
        if max_candidates > 90:
            return {"error": "Max candidates exceeded for direct execution"}, 400
        
        # 非同期処理の実行
        result = asyncio.run(
            process_search(search_id, requirement_id, search_params, max_candidates)
        )
        
        return result, 200
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return {"error": str(e)}, 500

async def process_search(
    search_id: str,
    requirement_id: str,
    search_params: Dict,
    max_candidates: int
) -> Dict:
    """検索処理のメイン実行"""
    
    # BigQueryクライアントの初期化
    bq_client = bigquery.Client()
    dataset_id = os.getenv("BIGQUERY_DATASET")
    
    try:
        # 1. 採用要件の取得
        requirement = await get_requirement(bq_client, dataset_id, requirement_id)
        if not requirement:
            raise ValueError(f"Requirement {requirement_id} not found")
        
        # 2. 検索ステータスを更新
        await update_search_status(bq_client, dataset_id, search_id, "in_progress")
        
        # 3. 候補者検索の実行（ダミー実装）
        search_handler = SearchHandler()
        candidates = await search_handler.search_candidates(
            search_params,
            max_candidates
        )
        
        logger.info(f"Found {len(candidates)} candidates")
        
        # 4. AI評価の実行
        ai_evaluator = AIEvaluator()
        evaluated_candidates = []
        
        for candidate in candidates:
            evaluation = await ai_evaluator.evaluate_candidate(
                candidate,
                requirement
            )
            evaluated_candidates.append({
                **candidate,
                "ai_evaluation": evaluation
            })
        
        # 5. 結果をBigQueryに保存
        await save_candidates(
            bq_client,
            dataset_id,
            search_id,
            evaluated_candidates
        )
        
        # 6. 検索ステータスを完了に更新
        await update_search_status(
            bq_client,
            dataset_id,
            search_id,
            "completed",
            len(evaluated_candidates)
        )
        
        # 7. 完了通知をPub/Subに送信
        await publish_completion_message(search_id, len(evaluated_candidates))
        
        return {
            "search_id": search_id,
            "status": "completed",
            "candidates_found": len(evaluated_candidates),
            "message": "Search completed successfully"
        }
        
    except Exception as e:
        logger.error(f"Error in process_search: {str(e)}")
        # エラー時はステータスを更新
        await update_search_status(bq_client, dataset_id, search_id, "failed", error=str(e))
        raise

async def get_requirement(bq_client, dataset_id: str, requirement_id: str) -> Dict:
    """BigQueryから採用要件を取得"""
    query = f"""
    SELECT *
    FROM `{dataset_id}.requirements`
    WHERE id = @requirement_id
    """
    
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("requirement_id", "STRING", requirement_id)
        ]
    )
    
    query_job = bq_client.query(query, job_config=job_config)
    results = list(query_job.result())
    
    if results:
        return dict(results[0])
    return None

async def update_search_status(
    bq_client,
    dataset_id: str,
    search_id: str,
    status: str,
    candidates_count: int = None,
    error: str = None
):
    """検索ステータスを更新"""
    table_id = f"{bq_client.project}.{dataset_id}.searches"
    table = bq_client.get_table(table_id)
    
    update_data = {
        "search_id": search_id,
        "status": status,
        "updated_at": datetime.utcnow().isoformat()
    }
    
    if candidates_count is not None:
        update_data["candidates_count"] = candidates_count
    if error:
        update_data["error_message"] = error
    
    # 実際の実装では、UPDATE文を使用
    logger.info(f"Updated search {search_id} status to {status}")

async def save_candidates(
    bq_client,
    dataset_id: str,
    search_id: str,
    candidates: List[Dict]
):
    """候補者データをBigQueryに保存"""
    table_id = f"{bq_client.project}.{dataset_id}.candidates"
    
    rows_to_insert = []
    for candidate in candidates:
        row = {
            "search_id": search_id,
            "candidate_data": json.dumps(candidate),
            "ai_score": candidate["ai_evaluation"]["score"],
            "ai_summary": candidate["ai_evaluation"]["summary"],
            "created_at": datetime.utcnow().isoformat()
        }
        rows_to_insert.append(row)
    
    errors = bq_client.insert_rows_json(table_id, rows_to_insert)
    if errors:
        logger.error(f"Failed to insert candidates: {errors}")
        raise Exception("Failed to save candidates")
    
    logger.info(f"Saved {len(candidates)} candidates to BigQuery")

async def publish_completion_message(search_id: str, candidates_count: int):
    """完了通知をPub/Subに送信"""
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(
        os.getenv("GOOGLE_CLOUD_PROJECT"),
        os.getenv("PUBSUB_RESULT_TOPIC", "scraping-results")
    )
    
    message = {
        "search_id": search_id,
        "status": "completed",
        "candidates_count": candidates_count,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    data = json.dumps(message).encode("utf-8")
    future = publisher.publish(topic_path, data)
    future.result()
    
    logger.info(f"Published completion message for search {search_id}")

@functions_framework.cloud_event
def search_candidates_pubsub(cloud_event):
    """
    Pub/Subトリガーによる候補者検索
    エージェントからのリクエストを処理
    """
    import base64
    
    # Pub/Subメッセージのデコード
    message = base64.b64decode(cloud_event.data["message"]["data"]).decode()
    request_data = json.loads(message)
    
    # HTTPハンドラーと同じ処理を実行
    class MockRequest:
        def get_json(self, silent=False):
            return request_data
    
    return search_candidates(MockRequest())