"""
Assignment Management API Router
Provides CRUD operations for assignments.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Job, Technician, JobStatus
from app.models.assignment import Assignment, AssignmentStatus
from app.schemas.assignment import AssignmentOut, AssignmentUpdate, AssignmentDetail

router = APIRouter(tags=["Assignments"])


# ====================== Endpoints ======================

@router.get("", response_model=List[AssignmentOut])
@router.get("/", response_model=List[AssignmentOut], include_in_schema=False)
def list_assignments(
    status: Optional[str] = None,
    run_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    List all assignments with optional filters.
    """
    query = db.query(Assignment).options(
        joinedload(Assignment.job),
        joinedload(Assignment.technician),
    )

    if status:
        try:
            query = query.filter(Assignment.status == AssignmentStatus(status))
        except ValueError:
            valid = [s.value for s in AssignmentStatus]
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status '{status}'. Valid: {valid}",
            )

    if run_id:
        query = query.filter(Assignment.run_id == run_id)

    assignments = (
        query.order_by(Assignment.scheduled_start).offset(offset).limit(limit).all()
    )
    return assignments


@router.get("/technician/{technician_id}", response_model=List[AssignmentDetail])
def get_technician_assignments(
    technician_id: str,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Get all assignments for a specific technician."""
    tech = db.query(Technician).filter(Technician.id == technician_id).first()
    if not tech:
        raise HTTPException(status_code=404, detail="Technician not found")

    query = db.query(Assignment).options(
        joinedload(Assignment.job),
        joinedload(Assignment.technician),
    ).filter(Assignment.technician_id == technician_id)

    if status:
        try:
            query = query.filter(Assignment.status == AssignmentStatus(status))
        except ValueError:
            pass

    assignments = query.order_by(Assignment.scheduled_start).all()

    results = []
    for a in assignments:
        job = a.job
        detail = AssignmentDetail(
            id=a.id,
            job_id=a.job_id,
            technician_id=a.technician_id,
            scheduled_start=a.scheduled_start,
            scheduled_end=a.scheduled_end,
            travel_before_minutes=a.travel_before_minutes,
            status=a.status.value if a.status else "pending",
            run_id=a.run_id,
            created_at=getattr(a, "created_at", None),
            updated_at=getattr(a, "updated_at", None),
            job_title=job.title if job else None,
            job_location=job.location if job else None,
            job_priority=job.priority.value if job and job.priority else None,
            technician_name=tech.name,
        )
        results.append(detail)

    return results


@router.get("/{assignment_id}", response_model=AssignmentDetail)
def get_assignment(
    assignment_id: str,
    db: Session = Depends(get_db),
):
    """Get a specific assignment by ID."""
    assignment = (
        db.query(Assignment)
        .options(
            joinedload(Assignment.job),
            joinedload(Assignment.technician),
        )
        .filter(Assignment.id == assignment_id)
        .first()
    )

    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    job = assignment.job
    tech = assignment.technician

    return AssignmentDetail(
        id=assignment.id,
        job_id=assignment.job_id,
        technician_id=assignment.technician_id,
        scheduled_start=assignment.scheduled_start,
        scheduled_end=assignment.scheduled_end,
        travel_before_minutes=assignment.travel_before_minutes,
        status=assignment.status.value if assignment.status else "pending",
        run_id=assignment.run_id,
        created_at=getattr(assignment, "created_at", None),
        updated_at=getattr(assignment, "updated_at", None),
        job_title=job.title if job else None,
        job_location=job.location if job else None,
        job_priority=job.priority.value if job and job.priority else None,
        technician_name=tech.name if tech else None,
    )


@router.patch("/{assignment_id}", response_model=AssignmentOut)
def update_assignment(
    assignment_id: str,
    update: AssignmentUpdate,
    db: Session = Depends(get_db),
):
    """
    Update assignment status or timing.

    Allowed status transitions:
    - pending → in_progress → completed
    """
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()

    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    if update.status is not None:
        try:
            new_status = AssignmentStatus(update.status)
        except ValueError:
            valid = [s.value for s in AssignmentStatus]
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status '{update.status}'. Valid: {valid}",
            )
        assignment.status = new_status

        # Sync Job status with assignment status
        job = db.query(Job).filter(Job.id == assignment.job_id).first()
        if job:
            if new_status == AssignmentStatus.IN_PROGRESS:
                job.status = JobStatus.IN_PROGRESS
            elif new_status == AssignmentStatus.COMPLETED:
                job.status = JobStatus.COMPLETED
            elif new_status == AssignmentStatus.PENDING:
                job.status = JobStatus.ASSIGNED

    if update.scheduled_start is not None:
        assignment.scheduled_start = update.scheduled_start

    if update.scheduled_end is not None:
        assignment.scheduled_end = update.scheduled_end

    if update.travel_before_minutes is not None:
        assignment.travel_before_minutes = update.travel_before_minutes

    db.commit()
    db.refresh(assignment)
    return assignment


@router.delete("/{assignment_id}")
def delete_assignment(
    assignment_id: str,
    db: Session = Depends(get_db),
):
    """
    Remove an assignment (unassign the job).
    The job's status will be reset to 'unassigned'.
    """
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()

    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    if assignment.status == AssignmentStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail="Cannot remove a completed assignment",
        )

    if assignment.status == AssignmentStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=400,
            detail="Cannot remove an in-progress assignment. Complete it first.",
        )

    # Reset job status
    job = db.query(Job).filter(Job.id == assignment.job_id).first()
    if job:
        job.status = JobStatus.UNASSIGNED

    db.delete(assignment)
    db.commit()

    return {"message": f"Assignment {assignment_id} removed; job is now unassigned"}
