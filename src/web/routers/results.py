from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime, date
from pydantic import BaseModel
import json

router = APIRouter()

class CandidateSummary(BaseModel):
    id: str
    bizreach_id: str
    name: str
    title: str
    company: str
    experience_years: int
    skills: List[str]
    ai_score: float
    recommendation: str
    evaluation_details: dict

class SearchResultSummary(BaseModel):
    search_id: str
    requirement_id: str
    requirement_title: str
    client_name: str
    started_at: datetime
    completed_at: Optional[datetime]
    status: str
    total_candidates: int
    highly_recommended: int
    recommended: int
    not_recommended: int
    average_score: float
    sheets_url: Optional[str]

class ClientReport(BaseModel):
    client_id: str
    client_name: str
    period_start: date
    period_end: date
    total_searches: int
    total_candidates: int
    success_rate: float
    average_processing_time: float
    top_skills: List[dict]

@router.get("/searches", response_model=List[SearchResultSummary])
async def list_search_results(
    client_id: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    skip: int = 0,
    limit: int = 100
):
    return []

@router.get("/searches/{search_id}", response_model=SearchResultSummary)
async def get_search_result(search_id: str):
    raise HTTPException(status_code=404, detail="Search result not found")

@router.get("/searches/{search_id}/candidates", response_model=List[CandidateSummary])
async def get_search_candidates(
    search_id: str,
    recommendation: Optional[str] = None,
    min_score: Optional[float] = None,
    skip: int = 0,
    limit: int = 100
):
    return []

@router.get("/reports/client/{client_id}", response_model=ClientReport)
async def get_client_report(
    client_id: str,
    start_date: date = Query(..., description="Report period start date"),
    end_date: date = Query(..., description="Report period end date")
):
    return ClientReport(
        client_id=client_id,
        client_name="Sample Client",
        period_start=start_date,
        period_end=end_date,
        total_searches=0,
        total_candidates=0,
        success_rate=0.0,
        average_processing_time=0.0,
        top_skills=[]
    )

@router.get("/stats/overview")
async def get_system_stats():
    return {
        "total_clients": 0,
        "active_requirements": 0,
        "searches_today": 0,
        "candidates_evaluated": 0,
        "average_accuracy": 0.0
    }

@router.post("/export/{search_id}")
async def export_to_sheets(search_id: str):
    return {
        "message": "Export completed",
        "sheets_url": f"https://docs.google.com/spreadsheets/d/dummy-{search_id}"
    }