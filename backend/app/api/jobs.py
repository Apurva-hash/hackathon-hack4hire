"""Job API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.schemas.job import JobCreate, JobUpdate, JobResponse, JobListResponse
from app.schemas.common import MessageResponse
from app.services.job_service import JobService
from app.models.job import JobStatus

router = APIRouter()


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=JobResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
def create_job(job_data: JobCreate, db: Session = Depends(get_db)):
    """Create a new job."""
    job = JobService.create_job(db, job_data)
    return job


@router.get("", response_model=JobListResponse)
@router.get("/", response_model=JobListResponse, include_in_schema=False)
def list_jobs(
    status_filter: Optional[JobStatus] = Query(None, alias="status"),
    priority: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """List jobs with optional filters."""
    jobs, total = JobService.list_jobs(
        db,
        status=status_filter,
        priority=priority,
        skip=skip,
        limit=limit
    )
    return JobListResponse(total=total, jobs=jobs)


@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: str, db: Session = Depends(get_db)):
    """Get a job by ID."""
    job = JobService.get_job(db, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    return job


@router.patch("/{job_id}", response_model=JobResponse)
def update_job(job_id: str, job_data: JobUpdate, db: Session = Depends(get_db)):
    """Update a job."""
    job = JobService.update_job(db, job_id, job_data)
    return job


@router.post("/{job_id}/cancel", response_model=JobResponse)
def cancel_job(job_id: str, db: Session = Depends(get_db)):
    """Cancel a job."""
    job = JobService.cancel_job(db, job_id)
    return job


@router.delete("/{job_id}", response_model=MessageResponse)
def delete_job(job_id: str, db: Session = Depends(get_db)):
    """Delete a job (soft delete by cancelling)."""
    job = JobService.cancel_job(db, job_id)
    return MessageResponse(
        message="Job cancelled successfully",
        detail=f"Job {job_id} has been cancelled"
    )
