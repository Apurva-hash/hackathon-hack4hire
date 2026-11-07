"""
Disruption Events API Router - Phase 7
Handles detection, analysis, and recovery from schedule disruptions.
"""

import json
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import (
    DisruptionEvent, DisruptionEventType, SchedulingRun,
    Job, Technician, TriggerType, JobStatus, AssignmentStatus
)
from app.models.assignment import Assignment
from app.schemas.disruption import DisruptionCreate, DisruptionOut, DisruptionProcessResult
from app.models.base import generate_uuid
from app.scheduler.engine import SchedulingEngine
from app.scheduler.alns_optimizer import ALNSConfig
from app.scheduler.disruption_handler import DisruptionDetector, DisruptionRecovery, RecoveryStrategy
from app.config import Config

router = APIRouter(tags=["Disruptions"])


# ====================== Endpoints ======================

@router.post("", response_model=DisruptionOut, status_code=201)
@router.post("/", response_model=DisruptionOut, status_code=201, include_in_schema=False)
def report_disruption(
    payload: DisruptionCreate,
    db: Session = Depends(get_db)
):
    """
    Report a new disruption event.

    Disruption types:
    - technician_unavailable
    - urgent_job
    - duration_change
    - job_cancellation
    - early_completion
    - late_completion
    """
    # Validate event_type
    try:
        event_type_enum = DisruptionEventType(payload.event_type)
    except ValueError:
        valid = [e.value for e in DisruptionEventType]
        raise HTTPException(
            status_code=400,
            detail=f"Invalid event_type '{payload.event_type}'. Valid values: {valid}"
        )

    # Validate the affected entity exists
    if payload.affected_entity_type == "technician":
        entity = db.query(Technician).filter(Technician.id == payload.affected_entity_id).first()
        if not entity:
            raise HTTPException(
                status_code=404,
                detail=f"Technician {payload.affected_entity_id} not found"
            )
    elif payload.affected_entity_type == "job":
        entity = db.query(Job).filter(Job.id == payload.affected_entity_id).first()
        if not entity:
            raise HTTPException(
                status_code=404,
                detail=f"Job {payload.affected_entity_id} not found"
            )
    else:
        raise HTTPException(
            status_code=400,
            detail="affected_entity_type must be 'technician' or 'job'"
        )

    # Serialize payload dict to JSON text
    payload_text = json.dumps(payload.payload) if payload.payload else None

    disruption = DisruptionEvent(
        event_type=event_type_enum,
        affected_entity_type=payload.affected_entity_type,
        affected_entity_id=payload.affected_entity_id,
        event_time=payload.event_time or datetime.utcnow(),
        payload=payload_text,
    )
    db.add(disruption)
    db.commit()
    db.refresh(disruption)

    return disruption


@router.get("/stats")
def get_disruption_stats(
    db: Session = Depends(get_db)
):
    """Get disruption statistics."""
    total = db.query(DisruptionEvent).count()

    by_type = {}
    for event_type in DisruptionEventType:
        count = (
            db.query(DisruptionEvent)
            .filter(DisruptionEvent.event_type == event_type)
            .count()
        )
        by_type[event_type.value] = count

    processed = (
        db.query(DisruptionEvent)
        .filter(DisruptionEvent.processed_run_id.isnot(None))
        .count()
    )
    unprocessed = total - processed

    return {
        "total_disruptions": total,
        "processed": processed,
        "unprocessed": unprocessed,
        "by_type": by_type,
    }


@router.get("/", response_model=List[DisruptionOut])
def list_disruptions(
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    event_type: Optional[str] = None,
    processed: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """List disruption events with optional filtering."""
    query = db.query(DisruptionEvent).order_by(DisruptionEvent.event_time.desc())

    if event_type:
        try:
            query = query.filter(DisruptionEvent.event_type == DisruptionEventType(event_type))
        except ValueError:
            pass

    if processed is True:
        query = query.filter(DisruptionEvent.processed_run_id.isnot(None))
    elif processed is False:
        query = query.filter(DisruptionEvent.processed_run_id.is_(None))

    disruptions = query.offset(offset).limit(limit).all()
    return disruptions


@router.get("/{disruption_id}", response_model=DisruptionOut)
def get_disruption(
    disruption_id: str,
    db: Session = Depends(get_db)
):
    """Get a specific disruption event by ID."""
    disruption = db.query(DisruptionEvent).filter(
        DisruptionEvent.id == disruption_id
    ).first()

    if not disruption:
        raise HTTPException(status_code=404, detail="Disruption event not found")

    return disruption


@router.post("/{disruption_id}/process", response_model=DisruptionProcessResult)
def process_disruption(
    disruption_id: str,
    db: Session = Depends(get_db)
):
    """
    Process a disruption event by triggering re-optimization.

    This endpoint:
    1. Looks up the disruption event
    2. Applies the disruption effect (e.g., marks technician unavailable)
    3. Triggers re-scheduling for affected jobs
    4. Links the resulting scheduling run to the disruption event
    """
    disruption = db.query(DisruptionEvent).filter(
        DisruptionEvent.id == disruption_id
    ).first()

    if not disruption:
        raise HTTPException(status_code=404, detail="Disruption event not found")

    if disruption.processed_run_id:
        return DisruptionProcessResult(
            disruption_id=disruption_id,
            run_id=disruption.processed_run_id,
            status="already_processed",
            message="This disruption has already been processed",
        )

    jobs_to_reschedule: List[Job] = []
    result_msg = ""
    trigger_type = TriggerType.REOPTIMIZATION

    # ---- Handle each disruption type ----
    if disruption.event_type == DisruptionEventType.TECHNICIAN_UNAVAILABLE:
        trigger_type = TriggerType.TECHNICIAN_UNAVAILABLE
        tech = db.query(Technician).filter(
            Technician.id == disruption.affected_entity_id
        ).first()
        if not tech:
            raise HTTPException(status_code=404, detail="Affected technician not found")

        # Find all PENDING assignments for this technician and unassign them
        affected_assignments = (
            db.query(Assignment)
            .filter(
                Assignment.technician_id == tech.id,
                Assignment.status == AssignmentStatus.PENDING,
            )
            .all()
        )
        for a in affected_assignments:
            job = db.query(Job).filter(Job.id == a.job_id).first()
            if job:
                job.status = JobStatus.UNASSIGNED
                jobs_to_reschedule.append(job)
            db.delete(a)

        db.commit()
        result_msg = (
            f"Technician {tech.name} marked unavailable; "
            f"{len(jobs_to_reschedule)} jobs freed for rescheduling"
        )

    elif disruption.event_type == DisruptionEventType.URGENT_JOB:
        trigger_type = TriggerType.URGENT_JOB
        job = db.query(Job).filter(Job.id == disruption.affected_entity_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Affected job not found")
        jobs_to_reschedule = [job]
        result_msg = f"Urgent job {job.title} queued for immediate scheduling"

    elif disruption.event_type == DisruptionEventType.JOB_CANCELLATION:
        trigger_type = TriggerType.JOB_CANCELLATION
        job = db.query(Job).filter(Job.id == disruption.affected_entity_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Affected job not found")
        job.status = JobStatus.CANCELLED
        if job.assignment:
            db.delete(job.assignment)
        db.commit()
        # No rescheduling needed — just confirm the cancellation
        disruption.processed_run_id = None
        db.commit()
        return DisruptionProcessResult(
            disruption_id=disruption_id,
            run_id=None,
            status="processed",
            message=f"Job {job.title} cancelled and assignment removed",
        )

    elif disruption.event_type in (
        DisruptionEventType.DURATION_CHANGE,
        DisruptionEventType.EARLY_COMPLETION,
        DisruptionEventType.LATE_COMPLETION,
    ):
        job = db.query(Job).filter(Job.id == disruption.affected_entity_id).first()
        if job:
            jobs_to_reschedule = [job]
        result_msg = f"Job affected by {disruption.event_type.value}; re-evaluating schedule"

    # ---- Run re-scheduling if there are jobs to reschedule ----
    run_id = None
    reassigned = 0
    unassigned_count = 0

    if jobs_to_reschedule:
        technicians = (
            db.query(Technician)
            .options(
                joinedload(Technician.skills),
                joinedload(Technician.service_zones),
                joinedload(Technician.availability_blocks),
            )
            .all()
        )

        for job in jobs_to_reschedule:
            if not hasattr(job, "required_skills") or not job.required_skills:
                db.refresh(job)

        config = Config()
        alns_config = ALNSConfig(max_iterations=50)  # lighter run for disruption recovery
        engine = SchedulingEngine(config, alns_config)

        try:
            results = engine.run_scheduling(
                jobs=jobs_to_reschedule,
                technicians=technicians,
                db=db,
                use_alns=True,
                algorithm="auto",
                trigger_type=trigger_type,
                trigger_description=f"Re-scheduling after disruption: {disruption.event_type.value}",
            )
            run_id = results["run_id"]

            if "alns" in results:
                fr = results["alns"]
            else:
                fr = results.get("greedy", {})

            reassigned = fr.get("assigned_count", 0)
            unassigned_count = fr.get("unassigned_count", 0)

            # Persist assignments to DB and update job statuses
            final_assignments = fr.get("assignments", [])
            for a in final_assignments:
                a.run_id = run_id
                # Check for existing assignment (unique constraint on job_id)
                existing = db.query(Assignment).filter(Assignment.job_id == a.job_id).first()
                if existing:
                    existing.technician_id = a.technician_id
                    existing.scheduled_start = a.scheduled_start
                    existing.scheduled_end = a.scheduled_end
                    existing.travel_before_minutes = getattr(a, "travel_before_minutes", 0)
                    existing.run_id = run_id
                else:
                    db.add(a)
                job_obj = db.query(Job).filter(Job.id == a.job_id).first()
                if job_obj:
                    job_obj.status = JobStatus.ASSIGNED
            db.commit()

        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Re-scheduling failed: {str(exc)}"
            )

    # Mark disruption as processed
    disruption.processed_run_id = run_id
    db.commit()

    return DisruptionProcessResult(
        disruption_id=disruption_id,
        run_id=run_id,
        status="processed",
        message=result_msg or "Disruption processed",
        jobs_reassigned=reassigned,
        jobs_unassigned=unassigned_count,
    )


# ====================== Phase 7: Enhanced Disruption Handling ======================

@router.post("/technician-unavailable")
def report_technician_unavailable(
    technician_id: str,
    unavailable_from: datetime,
    unavailable_until: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """
    Report a technician becoming unavailable.
    
    This will automatically:
    1. Detect affected assignments
    2. Analyze impact
    3. Execute recovery strategy
    """
    detector = DisruptionDetector(db)
    recovery = DisruptionRecovery(db)
    
    # Detect disruption
    event = detector.detect_technician_unavailability(
        technician_id=technician_id,
        unavailable_from=unavailable_from,
        unavailable_until=unavailable_until
    )
    
    if not event:
        return {
            "status": "no_impact",
            "message": "No assignments affected by technician unavailability"
        }
    
    # Analyze impact
    impact = recovery.analyze_impact(event)
    
    # Execute recovery
    run = recovery.recover_from_disruption(event, impact)
    
    return {
        "disruption_id": str(event.id),
        "impact_level": event.impact_level.value,
        "affected_assignments": len(impact.affected_assignments),
        "recovery_strategy": impact.recovery_strategy.value,
        "recovery_run_id": str(run.id),
        "recovery_successful": run.metrics.get("recovery_successful", False),
        "reason": impact.reason
    }


@router.post("/job-cancellation")
def report_job_cancellation(
    job_id: str,
    db: Session = Depends(get_db)
):
    """
    Report a job cancellation.
    
    This will automatically:
    1. Detect if job had an assignment
    2. Analyze impact on schedule
    3. Execute recovery (optimization to fill gap)
    """
    detector = DisruptionDetector(db)
    recovery = DisruptionRecovery(db)
    
    # Detect disruption
    event = detector.detect_job_cancellation(job_id=job_id)
    
    if not event:
        # Job wasn't scheduled, just cancel it
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = JobStatus.CANCELLED
            db.commit()
        
        return {
            "status": "cancelled",
            "message": "Job cancelled (was not scheduled)"
        }
    
    # Analyze impact
    impact = recovery.analyze_impact(event)
    
    # Execute recovery
    run = recovery.recover_from_disruption(event, impact)
    
    return {
        "disruption_id": str(event.id),
        "impact_level": event.impact_level.value,
        "affected_assignments": len(impact.affected_assignments),
        "downstream_jobs": len(impact.downstream_conflicts),
        "recovery_strategy": impact.recovery_strategy.value,
        "recovery_run_id": str(run.id),
        "reason": impact.reason
    }


@router.post("/emergency-job")
def report_emergency_job(
    job_id: str,
    db: Session = Depends(get_db)
):
    """
    Report an emergency job that requires immediate scheduling.
    
    This will automatically:
    1. Detect eligible technicians
    2. Analyze insertion points
    3. Execute incremental insertion
    """
    detector = DisruptionDetector(db)
    recovery = DisruptionRecovery(db)
    
    # Detect disruption
    event = detector.detect_emergency_job(job_id=job_id)
    
    if not event:
        return {
            "status": "not_emergency",
            "message": "Job is not marked as CRITICAL priority"
        }
    
    # Analyze impact
    impact = recovery.analyze_impact(event)
    
    # Execute recovery
    run = recovery.recover_from_disruption(event, impact)
    
    return {
        "disruption_id": str(event.id),
        "impact_level": event.impact_level.value,
        "eligible_technicians": len(impact.affected_technicians),
        "recovery_strategy": impact.recovery_strategy.value,
        "recovery_run_id": str(run.id),
        "job_assigned": run.metrics.get("emergency_job_assigned", False),
        "assigned_to": run.metrics.get("assigned_to"),
        "scheduled_start": run.metrics.get("scheduled_start"),
        "reason": impact.reason
    }


@router.get("/impact-analysis/{disruption_id}")
def get_disruption_impact_analysis(
    disruption_id: str,
    db: Session = Depends(get_db)
):
    """
    Get detailed impact analysis for a disruption event.
    
    Returns:
    - Affected assignments
    - Affected jobs
    - Affected technicians
    - Impact score
    - Recommended recovery strategy
    """
    event = db.query(DisruptionEvent).filter(DisruptionEvent.id == disruption_id).first()
    
    if not event:
        raise HTTPException(status_code=404, detail="Disruption event not found")
    
    recovery = DisruptionRecovery(db)
    impact = recovery.analyze_impact(event)
    
    return {
        "disruption_id": str(event.id),
        "disruption_type": event.disruption_type.value,
        "impact_score": impact.impact_score,
        "impact_level": event.impact_level.value,
        "recovery_strategy": impact.recovery_strategy.value,
        "reason": impact.reason,
        "affected_summary": {
            "assignments": len(impact.affected_assignments),
            "jobs": len(impact.affected_jobs),
            "technicians": len(impact.affected_technicians),
            "downstream_conflicts": len(impact.downstream_conflicts)
        },
        "affected_details": {
            "assignments": [
                {
                    "id": str(a.id),
                    "job_id": str(a.job_id),
                    "job_title": a.job.title,
                    "technician_id": str(a.technician_id),
                    "technician_name": a.technician.name,
                    "scheduled_start": a.scheduled_start.isoformat(),
                    "scheduled_end": a.scheduled_end.isoformat()
                }
                for a in impact.affected_assignments
            ],
            "jobs": [
                {
                    "id": str(j.id),
                    "title": j.title,
                    "priority": j.priority,
                    "status": j.status.value
                }
                for j in impact.affected_jobs
            ],
            "technicians": [
                {
                    "id": str(t.id),
                    "name": t.name,
                    "is_active": t.is_active
                }
                for t in impact.affected_technicians
            ]
        }
    }


@router.post("/recover/{disruption_id}")
def execute_recovery(
    disruption_id: str,
    db: Session = Depends(get_db)
):
    """
    Manually trigger recovery for a disruption event.
    
    This allows you to:
    1. Re-analyze the impact
    2. Execute the recommended recovery strategy
    3. Get detailed results
    """
    event = db.query(DisruptionEvent).filter(DisruptionEvent.id == disruption_id).first()
    
    if not event:
        raise HTTPException(status_code=404, detail="Disruption event not found")
    
    recovery = DisruptionRecovery(db)
    
    # Analyze impact
    impact = recovery.analyze_impact(event)
    
    # Execute recovery
    run = recovery.recover_from_disruption(event, impact)
    
    return {
        "disruption_id": str(event.id),
        "recovery_run_id": str(run.id),
        "recovery_strategy": impact.recovery_strategy.value,
        "status": run.status,
        "started_at": run.started_at.isoformat(),
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "metrics": run.metrics,
        "impact_analysis": {
            "impact_score": impact.impact_score,
            "affected_assignments": len(impact.affected_assignments),
            "affected_jobs": len(impact.affected_jobs),
            "reason": impact.reason
        }
    }


@router.get("/recovery-runs")
def list_recovery_runs(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    List all recovery scheduling runs.
    
    Shows history of disruption recovery operations.
    """
    runs = (
        db.query(SchedulingRun)
        .filter(
            SchedulingRun.config.contains('"recovery_strategy"')
        )
        .order_by(SchedulingRun.started_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    
    return [
        {
            "id": str(run.id),
            "algorithm": run.algorithm,
            "status": run.status,
            "started_at": run.started_at.isoformat(),
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            "recovery_strategy": run.config.get("recovery_strategy"),
            "disruption_event_id": run.config.get("disruption_event_id"),
            "metrics": run.metrics
        }
        for run in runs
    ]
