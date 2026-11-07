"""Job service - Business logic for job management."""

from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from fastapi import HTTPException, status

from app.models import Job, JobStatus, Skill
from app.schemas.job import JobCreate, JobUpdate


class JobService:
    """Service for job-related operations."""
    
    @staticmethod
    def create_job(db: Session, job_data: JobCreate) -> Job:
        """Create a new job."""
        from app.models.service_zone import ServiceZone

        # If service_zone_id is not specified, assign to first available zone
        zone_id = job_data.service_zone_id
        if not zone_id:
            first_zone = db.query(ServiceZone).first()
            if first_zone:
                zone_id = first_zone.id
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No service zones exist in the database to assign job."
                )
        else:
            service_zone = db.query(ServiceZone).filter(ServiceZone.id == zone_id).first()
            if not service_zone:
                # If invalid zone provided, fallback to first zone
                first_zone = db.query(ServiceZone).first()
                if first_zone:
                    zone_id = first_zone.id
                else:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Service zone {job_data.service_zone_id} not found"
                    )
        
        # Validate skills exist
        if job_data.required_skill_ids:
            skills = db.query(Skill).filter(Skill.id.in_(job_data.required_skill_ids)).all()
            if len(skills) != len(job_data.required_skill_ids):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="One or more required skills not found"
                )
        
        # Create job
        job = Job(
            title=job_data.title,
            description=job_data.description,
            location=job_data.location,
            service_zone_id=zone_id,
            duration_minutes=job_data.duration_minutes,
            time_window_start=job_data.time_window_start,
            time_window_end=job_data.time_window_end,
            sla_deadline=job_data.sla_deadline,
            priority=job_data.priority,
            status=JobStatus.PENDING,
        )
        
        # Add required skills
        if job_data.required_skill_ids:
            skills = db.query(Skill).filter(Skill.id.in_(job_data.required_skill_ids)).all()
            job.required_skills = skills
        
        db.add(job)
        db.commit()
        # Re-query with eager-loaded relationships to avoid lazy-load issues during serialization
        return JobService.get_job(db, job.id)
    
    @staticmethod
    def get_job(db: Session, job_id: str) -> Optional[Job]:
        """Get a job by ID."""
        return (
            db.query(Job)
            .options(
                joinedload(Job.required_skills),
                joinedload(Job.service_zone),
                joinedload(Job.assignment),
            )
            .filter(Job.id == job_id)
            .first()
        )
    
    @staticmethod
    def list_jobs(
        db: Session,
        status: Optional[JobStatus] = None,
        priority: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[Job], int]:
        """List jobs with optional filters."""
        query = db.query(Job).options(
            joinedload(Job.required_skills),
            joinedload(Job.service_zone),
            joinedload(Job.assignment),
        )
        
        if status:
            query = query.filter(Job.status == status)
        if priority:
            query = query.filter(Job.priority == priority)
        
        total = query.count()
        jobs = query.offset(skip).limit(limit).all()
        return jobs, total
    
    @staticmethod
    def update_job(db: Session, job_id: str, job_data: JobUpdate) -> Job:
        """Update a job."""
        job = JobService.get_job(db, job_id)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found"
            )
        
        # Validate state transition
        if job_data.status and not JobService._is_valid_status_transition(job.status, job_data.status):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status transition from {job.status} to {job_data.status}"
            )
        
        # Update fields
        update_data = job_data.model_dump(exclude_unset=True)
        
        # Handle required_skill_ids separately
        if 'required_skill_ids' in update_data:
            skill_ids = update_data.pop('required_skill_ids')
            if skill_ids is not None:
                skills = db.query(Skill).filter(Skill.id.in_(skill_ids)).all()
                if len(skills) != len(skill_ids):
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="One or more required skills not found"
                    )
                job.required_skills = skills
        
        for key, value in update_data.items():
            setattr(job, key, value)
        
        db.commit()
        # Re-query with eager-loaded relationships to avoid lazy-load issues
        return JobService.get_job(db, job_id)
    
    @staticmethod
    def cancel_job(db: Session, job_id: str) -> Job:
        """Cancel a job."""
        job = JobService.get_job(db, job_id)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found"
            )
        
        if job.status in [JobStatus.COMPLETED, JobStatus.CANCELLED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel job with status {job.status}"
            )
        
        job.status = JobStatus.CANCELLED
        db.commit()
        # Re-query with eager-loaded relationships to avoid lazy-load issues
        return JobService.get_job(db, job_id)
    
    @staticmethod
    def _is_valid_status_transition(current: JobStatus, new: JobStatus) -> bool:
        """Check if status transition is valid."""
        valid_transitions = {
            JobStatus.PENDING: [JobStatus.ASSIGNED, JobStatus.CANCELLED, JobStatus.UNASSIGNED],
            JobStatus.ASSIGNED: [JobStatus.IN_PROGRESS, JobStatus.CANCELLED, JobStatus.PENDING],
            JobStatus.UNASSIGNED: [JobStatus.ASSIGNED, JobStatus.CANCELLED, JobStatus.PENDING],
            JobStatus.IN_PROGRESS: [JobStatus.COMPLETED, JobStatus.CANCELLED],
            JobStatus.COMPLETED: [],  # Final state
            JobStatus.CANCELLED: [],  # Final state
        }
        return new in valid_transitions.get(current, [])
