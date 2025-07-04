from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
from enum import Enum
import uuid

router = APIRouter()

class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class JobType(str, Enum):
    SCRAPING = "scraping"
    AI_EVALUATION = "ai_evaluation"
    EXPORT = "export"

class JobCreate(BaseModel):
    requirement_id: str
    job_type: JobType
    parameters: Optional[dict] = {}
    scheduled_at: Optional[datetime] = None

class JobResponse(BaseModel):
    id: str
    requirement_id: str
    job_type: JobType
    status: JobStatus
    parameters: dict
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]
    result_summary: Optional[dict]

class JobUpdateStatus(BaseModel):
    status: JobStatus
    error_message: Optional[str] = None
    result_summary: Optional[dict] = None

@router.get("/", response_model=List[JobResponse])
async def list_jobs(
    requirement_id: Optional[str] = None,
    status: Optional[JobStatus] = None,
    job_type: Optional[JobType] = None,
    skip: int = 0,
    limit: int = 100
):
    return []

@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: str):
    raise HTTPException(status_code=404, detail="Job not found")

@router.post("/", response_model=JobResponse)
async def create_job(job: JobCreate, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    
    return JobResponse(
        id=job_id,
        requirement_id=job.requirement_id,
        job_type=job.job_type,
        status=JobStatus.PENDING,
        parameters=job.parameters,
        created_at=datetime.now(),
        started_at=None,
        completed_at=None,
        error_message=None,
        result_summary=None
    )

@router.put("/{job_id}/status", response_model=JobResponse)
async def update_job_status(job_id: str, status_update: JobUpdateStatus):
    raise HTTPException(status_code=404, detail="Job not found")

@router.post("/{job_id}/cancel")
async def cancel_job(job_id: str):
    return {"message": "Job cancelled successfully"}

@router.get("/{job_id}/logs")
async def get_job_logs(job_id: str, limit: int = 100):
    return {
        "job_id": job_id,
        "logs": []
    }

@router.post("/scrape/{requirement_id}")
async def start_scraping_job(requirement_id: str, background_tasks: BackgroundTasks):
    job = JobCreate(
        requirement_id=requirement_id,
        job_type=JobType.SCRAPING,
        parameters={"auto_evaluate": True}
    )
    return await create_job(job, background_tasks)