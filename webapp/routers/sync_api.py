"""
Sync monitoring API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from .auth import get_current_user_from_cookie
from core.utils.supabase_client import get_supabase_client
import json

router = APIRouter(
    prefix="/api/sync",
    tags=["sync"]
)

@router.get("/status")
async def get_sync_status(
    current_user: dict = Depends(get_current_user_from_cookie)
):
    """Get overall sync status summary"""
    if not current_user or current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    supabase = get_supabase_client()
    
    try:
        # Try to get sync status from view first
        try:
            response = supabase.table("sync_status").select("*").execute()
            if response.data:
                status = response.data[0]
                return {
                    "pending_count": status.get("pending_count", 0),
                    "synced_count": status.get("synced_count", 0),
                    "error_count": status.get("error_count", 0),
                    "last_sync_at": status.get("last_sync_at"),
                    "current_time": status.get("current_time")
                }
        except:
            # If view doesn't exist, calculate manually
            pass
        
        # Fallback: calculate sync status manually
        all_evaluations = supabase.table("client_evaluations").select("synced_to_pinecone, synced_at, sync_error").execute()
        
        if all_evaluations.data:
            pending_count = sum(1 for e in all_evaluations.data if not e.get("synced_to_pinecone", False))
            synced_count = sum(1 for e in all_evaluations.data if e.get("synced_to_pinecone", False))
            error_count = sum(1 for e in all_evaluations.data if e.get("sync_error"))
            
            # Get last sync time
            sync_times = [e.get("synced_at") for e in all_evaluations.data if e.get("synced_at")]
            last_sync_at = max(sync_times) if sync_times else None
        else:
            pending_count = synced_count = error_count = 0
            last_sync_at = None
        
        return {
            "pending_count": pending_count,
            "synced_count": synced_count,
            "error_count": error_count,
            "last_sync_at": last_sync_at,
            "current_time": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        import traceback
        print(f"Error in get_sync_status: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/errors")
async def get_sync_errors(
    limit: int = 10,
    current_user: dict = Depends(get_current_user_from_cookie)
):
    """Get recent sync errors"""
    if not current_user or current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    supabase = get_supabase_client()
    
    try:
        # Get evaluations with sync errors
        # First try with sync columns
        try:
            response = supabase.table("client_evaluations") \
                .select("id, candidate_id, requirement_id, sync_error, sync_retry_count, created_at") \
                .not_.is_("sync_error", "null") \
                .order("created_at", desc=True) \
                .limit(limit) \
                .execute()
            
            return response.data or []
        except:
            # If sync columns don't exist, return empty list
            return []
        
    except Exception as e:
        print(f"Error in get_sync_errors: {str(e)}")
        return []  # Return empty list instead of raising error

@router.get("/logs")
async def get_sync_logs(
    limit: int = 10,
    current_user: dict = Depends(get_current_user_from_cookie)
):
    """Get recent sync logs"""
    if not current_user or current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    supabase = get_supabase_client()
    
    try:
        # Get sync logs
        response = supabase.table("sync_logs") \
            .select("*") \
            .order("created_at", desc=True) \
            .limit(limit) \
            .execute()
        
        return response.data or []
        
    except Exception as e:
        # If table doesn't exist, return empty list
        print(f"Error in get_sync_logs: {str(e)}")
        return []

@router.get("/pending")
async def get_pending_evaluations(
    limit: int = 20,
    current_user: dict = Depends(get_current_user_from_cookie)
):
    """Get pending evaluations to sync"""
    if not current_user or current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    supabase = get_supabase_client()
    
    try:
        # Get pending evaluations with related data
        # First try with sync columns and proper table names
        try:
            response = supabase.table("client_evaluations") \
                .select("""
                    id,
                    candidate_id,
                    requirement_id,
                    client_evaluation,
                    client_feedback,
                    evaluation_date,
                    sync_error,
                    sync_retry_count,
                    created_at,
                    candidates!client_evaluations_candidate_id_fkey(name),
                    job_requirements!client_evaluations_requirement_id_fkey(title)
                """) \
                .eq("synced_to_pinecone", False) \
                .lt("sync_retry_count", 3) \
                .order("created_at", desc=True) \
                .limit(limit) \
                .execute()
        except Exception as e:
            print(f"First query failed: {e}")
            # If sync columns don't exist or relationships are different, try simpler query
            try:
                response = supabase.table("client_evaluations") \
                    .select("""
                        id,
                        candidate_id,
                        requirement_id,
                        client_evaluation,
                        client_feedback,
                        evaluation_date,
                        created_at
                    """) \
                    .order("created_at", desc=True) \
                    .limit(limit) \
                    .execute()
            except Exception as e2:
                print(f"Second query also failed: {e2}")
                response = None
        
        # Format the response
        evaluations = []
        if response and response.data:
            for item in response.data:
                # Extract candidate name - handle different response formats
                candidate_name = "N/A"
                if item.get("candidates"):
                    if isinstance(item["candidates"], dict):
                        candidate_name = item["candidates"].get("name", "N/A")
                    elif isinstance(item["candidates"], list) and len(item["candidates"]) > 0:
                        candidate_name = item["candidates"][0].get("name", "N/A")
                
                # Extract requirement title - handle different response formats
                requirement_title = "N/A"
                if item.get("job_requirements"):
                    if isinstance(item["job_requirements"], dict):
                        requirement_title = item["job_requirements"].get("title", "N/A")
                    elif isinstance(item["job_requirements"], list) and len(item["job_requirements"]) > 0:
                        requirement_title = item["job_requirements"][0].get("title", "N/A")
                
                evaluation = {
                    "id": item.get("id", ""),
                    "candidate_id": item.get("candidate_id", ""),
                    "requirement_id": item.get("requirement_id", ""),
                    "client_evaluation": item.get("client_evaluation", ""),
                    "client_feedback": item.get("client_feedback", ""),
                    "evaluation_date": item.get("evaluation_date"),
                    "sync_error": item.get("sync_error"),
                    "sync_retry_count": item.get("sync_retry_count", 0),
                    "created_at": item.get("created_at", ""),
                    "candidate_name": candidate_name,
                    "requirement_title": requirement_title
                }
                evaluations.append(evaluation)
        
        return evaluations
        
    except Exception as e:
        print(f"Error in get_pending_evaluations: {str(e)}")
        return []  # Return empty list instead of raising error

@router.post("/manual")
async def trigger_manual_sync(
    body: Dict[str, Any],
    current_user: dict = Depends(get_current_user_from_cookie)
):
    """Trigger manual sync via Edge Function"""
    if not current_user or current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    batch_size = body.get("batchSize", 50)
    supabase = get_supabase_client()
    
    try:
        # Call the manual sync function
        response = supabase.rpc(
            "manual_sync_evaluations",
            {"batch_size": batch_size}
        ).execute()
        
        if response.data:
            # Parse the response from Edge Function
            result = response.data
            if isinstance(result, str):
                try:
                    result = json.loads(result)
                except:
                    pass
            
            # Check if it's a successful response
            if isinstance(result, dict) and result.get("status_code") == 200:
                body_data = result.get("body", {})
                if isinstance(body_data, str):
                    try:
                        body_data = json.loads(body_data)
                    except:
                        body_data = {}
                
                return {
                    "success": True,
                    "results": body_data.get("results", {
                        "processed": 0,
                        "successful": 0,
                        "failed": 0
                    })
                }
            else:
                return {
                    "success": False,
                    "error": "Sync failed",
                    "details": result
                }
        
        return {
            "success": False,
            "error": "No response from sync function"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@router.post("/evaluation/{evaluation_id}")
async def sync_single_evaluation(
    evaluation_id: str,
    current_user: dict = Depends(get_current_user_from_cookie)
):
    """Sync a single evaluation"""
    if not current_user or current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    supabase = get_supabase_client()
    
    try:
        # First, reset the sync status for this evaluation
        update_response = supabase.table("client_evaluations") \
            .update({
                "synced_to_pinecone": False,
                "sync_error": None,
                "sync_retry_count": 0
            }) \
            .eq("id", evaluation_id) \
            .execute()
        
        if not update_response.data:
            return {
                "success": False,
                "error": "Evaluation not found"
            }
        
        # Trigger a manual sync with batch size 1
        sync_response = supabase.rpc(
            "manual_sync_evaluations",
            {"batch_size": 1}
        ).execute()
        
        return {
            "success": True,
            "message": "Sync triggered for evaluation"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }