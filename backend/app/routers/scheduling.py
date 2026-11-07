"""
Scheduling API Endpoints - Bug-fixed version
Trigger Greedy Insertion and ALNS optimization
"""

from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel, ConfigDict

from app.database import get_db
from app.models import (
    Job, Technician, SchedulingRun, SchedulingDecision, Assignment,
    RunStatus, TriggerType, Feasibility, JobStatus
)
from app.scheduler.engine import SchedulingEngine
from app.scheduler.alns_optimizer import ALNSConfig
from app.config import Config

router = APIRouter(prefix="/scheduling", tags=["Scheduling"])


# ====================== Request/Response Models ======================

class SchedulingRequest(BaseModel):
    """Request to trigger scheduling."""
    algorithm: str = "auto"          # "greedy", "alns", or "auto"
    use_alns: bool = True
    job_ids: Optional[List[str]] = None        # UUIDs, or None for all
    technician_ids: Optional[List[str]] = None  # UUIDs, or None for all
    trigger_type: str = "initial"              # matches TriggerType enum values
    trigger_description: Optional[str] = None

    # ALNS Configuration (optional overrides)
    max_iterations: Optional[int] = 100
    destroy_size_min: Optional[int] = 5
    destroy_size_max: Optional[int] = 20
    initial_temperature: Optional[float] = 100.0
    cooling_rate: Optional[float] = 0.95
    random_seed: Optional[int] = 42

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "algorithm": "auto",
                "use_alns": True,
                "max_iterations": 100,
                "destroy_size_min": 5,
                "destroy_size_max": 20,
            }
        }
    )


class AssignmentResponse(BaseModel):
    """Assignment in scheduling response."""
    job_id: str
    technician_id: str
    scheduled_start: str
    scheduled_end: str
    travel_before_minutes: int

    model_config = ConfigDict(from_attributes=True)


class MetricsResponse(BaseModel):
    """Scheduling metrics."""
    total_score: float
    job_coverage: float
    total_travel_time: float
    total_idle_time: float
    priority_fulfillment_rate: float
    technician_utilization: float = 0.0


class SchedulingResponse(BaseModel):
    """Scheduling execution result."""
    run_id: str
    status: str
    algorithm: str
    jobs_count: int
    technicians_count: int
    assigned_count: int
    unassigned_count: int
    execution_time: float
    metrics: MetricsResponse
    assignments: List[AssignmentResponse]
    comparison: Optional[dict] = None


class SchedulingRunSummary(BaseModel):
    """Summary of a past scheduling run."""
    id: str
    timestamp: Optional[str]
    status: str
    algorithm_used: str
    objective_score: Optional[float]
    total_travel_minutes: Optional[int]
    sla_violations: Optional[int]
    unassigned_high_priority: Optional[int]
    trigger_type: str


# ====================== Endpoints ======================

@router.post("/run", response_model=SchedulingResponse)
def run_scheduling(
    request: SchedulingRequest,
    db: Session = Depends(get_db)
):
    """
    Execute scheduling with Greedy Insertion and/or ALNS optimization.

    - **algorithm**: "greedy", "alns", or "auto" (both with comparison)
    - **use_alns**: Whether to run ALNS after greedy
    - **job_ids**: Specific job UUIDs to schedule (None = all pending jobs)
    - **technician_ids**: Specific technician UUIDs (None = all available)
    """
    # Load jobs
    job_query = db.query(Job).options(
        joinedload(Job.required_skills),
        joinedload(Job.service_zone),
    )

    if request.job_ids:
        job_query = job_query.filter(Job.id.in_(request.job_ids))
    else:
        # Default: only schedule pending/unassigned jobs
        job_query = job_query.filter(
            Job.status.in_([JobStatus.PENDING, JobStatus.UNASSIGNED])
        )

    jobs = job_query.all()

    if not jobs:
        raise HTTPException(status_code=404, detail="No jobs found to schedule")

    # Load technicians
    tech_query = db.query(Technician).options(
        joinedload(Technician.skills),
        joinedload(Technician.service_zones),
        joinedload(Technician.availability_blocks),
    )

    if request.technician_ids:
        tech_query = tech_query.filter(Technician.id.in_(request.technician_ids))

    technicians = tech_query.all()

    if not technicians:
        raise HTTPException(status_code=404, detail="No technicians found")

    # Map trigger_type string to enum
    try:
        trigger_type_enum = TriggerType(request.trigger_type)
    except ValueError:
        trigger_type_enum = TriggerType.INITIAL

    # Build ALNS config
    alns_config = ALNSConfig(
        max_iterations=request.max_iterations or 100,
        destroy_size_min=request.destroy_size_min or 5,
        destroy_size_max=request.destroy_size_max or 20,
        initial_temperature=request.initial_temperature or 100.0,
        cooling_rate=request.cooling_rate or 0.95,
        random_seed=request.random_seed or 42,
    )

    # Initialize engine
    config = Config()
    engine = SchedulingEngine(config, alns_config)

    try:
        results = engine.run_scheduling(
            jobs=jobs,
            technicians=technicians,
            db=db,
            use_alns=request.use_alns,
            algorithm=request.algorithm,
            trigger_type=trigger_type_enum,
            trigger_description=request.trigger_description,
        )

        # Determine which result to return
        if request.algorithm == "auto" and "alns" in results:
            final_results = results["alns"]
        elif request.algorithm == "alns" and "alns" in results:
            final_results = results["alns"]
        else:
            final_results = results["greedy"]

        # Build assignment responses
        assignments_response = [
            AssignmentResponse(
                job_id=a.job_id,
                technician_id=a.technician_id,
                scheduled_start=a.scheduled_start.isoformat(),
                scheduled_end=a.scheduled_end.isoformat(),
                travel_before_minutes=getattr(a, "travel_before_minutes", 0),  # correct field
            )
            for a in final_results["assignments"]
        ]

        metrics_data = final_results["metrics"]
        metrics_response = MetricsResponse(
            total_score=metrics_data.get("total_score", 0.0),
            job_coverage=metrics_data.get("job_coverage", 0.0),
            total_travel_time=metrics_data.get("total_travel_time", 0.0),
            total_idle_time=metrics_data.get("total_idle_time", 0.0),
            priority_fulfillment_rate=metrics_data.get("priority_fulfillment_rate", 0.0),
            technician_utilization=metrics_data.get("technician_utilization", 0.0),
        )

        return SchedulingResponse(
            run_id=results["run_id"],
            status=results["status"],
            algorithm=results["algorithm"],
            jobs_count=results["jobs_count"],
            technicians_count=results["technicians_count"],
            assigned_count=final_results["assigned_count"],
            unassigned_count=final_results["unassigned_count"],
            execution_time=results["execution_time"],
            metrics=metrics_response,
            assignments=assignments_response,
            comparison=results.get("comparison"),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scheduling failed: {str(e)}")


@router.get("/runs", response_model=List[SchedulingRunSummary])
def list_scheduling_runs(
    limit: int = Query(10, ge=1, le=100),
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List recent scheduling runs."""
    query = db.query(SchedulingRun).order_by(SchedulingRun.timestamp.desc())  # correct field

    if status:
        try:
            query = query.filter(SchedulingRun.status == RunStatus(status))
        except ValueError:
            pass

    runs = query.limit(limit).all()

    return [
        SchedulingRunSummary(
            id=run.id,
            timestamp=run.timestamp.isoformat() if run.timestamp else None,   # correct field
            status=run.status.value if run.status else "unknown",
            algorithm_used=run.algorithm_used,
            objective_score=run.objective_score,           # correct field
            total_travel_minutes=run.total_travel_minutes, # correct field
            sla_violations=run.sla_violations,
            unassigned_high_priority=run.unassigned_high_priority,
            trigger_type=run.trigger_type.value if run.trigger_type else "initial",
        )
        for run in runs
    ]


@router.get("/runs/{run_id}")
def get_scheduling_run(
    run_id: str,
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific scheduling run."""
    run = db.query(SchedulingRun).filter(SchedulingRun.id == run_id).first()

    if not run:
        raise HTTPException(status_code=404, detail="Scheduling run not found")

    # Get decisions using correct FK field name
    decisions = db.query(SchedulingDecision).filter(
        SchedulingDecision.run_id == run_id   # correct field: run_id
    ).all()

    # Use feasibility to distinguish assigned vs unassigned
    assigned = [d for d in decisions if d.feasibility == Feasibility.FEASIBLE]
    unassigned = [d for d in decisions if d.feasibility != Feasibility.FEASIBLE]

    return {
        "id": run.id,
        "timestamp": run.timestamp.isoformat() if run.timestamp else None,  # correct field
        "trigger_type": run.trigger_type.value if run.trigger_type else None,
        "trigger_description": run.trigger_description,
        "status": run.status.value if run.status else "unknown",
        "algorithm_used": run.algorithm_used,
        "algorithm_version": run.algorithm_version,
        "objective_score": run.objective_score,           # correct field
        "total_travel_minutes": run.total_travel_minutes, # correct field
        "sla_violations": run.sla_violations,
        "unassigned_high_priority": run.unassigned_high_priority,
        "overtime_minutes": run.overtime_minutes,
        "assignment_changes": run.assignment_changes,
        "error_message": run.error_message,
        "assigned_decisions": [
            {
                "job_id": d.job_id,
                "technician_id": d.technician_id,
                "scheduled_start": d.scheduled_start.isoformat() if d.scheduled_start else None,
                "feasibility": d.feasibility.value if d.feasibility else None,
                "selected_score": d.selected_score,
                "candidate_count": d.candidate_count,
                "explanation_text": d.explanation_text,
            }
            for d in assigned
        ],
        "unassigned_decisions": [
            {
                "job_id": d.job_id,
                "feasibility": d.feasibility.value if d.feasibility else None,
                "rejection_reason": d.rejection_reason.value if d.rejection_reason else None,
                "explanation_text": d.explanation_text,
            }
            for d in unassigned
        ],
    }


@router.delete("/runs/{run_id}")
def delete_scheduling_run(
    run_id: str,
    db: Session = Depends(get_db)
):
    """Delete a scheduling run and its decisions."""
    run = db.query(SchedulingRun).filter(SchedulingRun.id == run_id).first()

    if not run:
        raise HTTPException(status_code=404, detail="Scheduling run not found")

    # Delete decisions first (cascade should handle this, but be explicit)
    db.query(SchedulingDecision).filter(
        SchedulingDecision.run_id == run_id  # correct field
    ).delete()

    db.delete(run)
    db.commit()

    return {"message": f"Scheduling run {run_id} deleted successfully"}


@router.get("/compare/{run_id_1}/vs/{run_id_2}")
def compare_scheduling_runs(
    run_id_1: str,
    run_id_2: str,
    db: Session = Depends(get_db)
):
    """Compare two scheduling runs side by side."""
    run1 = db.query(SchedulingRun).filter(SchedulingRun.id == run_id_1).first()
    run2 = db.query(SchedulingRun).filter(SchedulingRun.id == run_id_2).first()

    if not run1 or not run2:
        raise HTTPException(status_code=404, detail="One or both runs not found")

    score1 = run1.objective_score or 0.0   # correct field
    score2 = run2.objective_score or 0.0   # correct field

    return {
        "run_1": {
            "id": run1.id,
            "algorithm": run1.algorithm_used,
            "objective_score": run1.objective_score,
            "total_travel_minutes": run1.total_travel_minutes,
            "sla_violations": run1.sla_violations,
        },
        "run_2": {
            "id": run2.id,
            "algorithm": run2.algorithm_used,
            "objective_score": run2.objective_score,
            "total_travel_minutes": run2.total_travel_minutes,
            "sla_violations": run2.sla_violations,
        },
        "comparison": {
            "score_delta": score2 - score1,
            "score_improvement_pct": (
                (score2 - score1) / score1 * 100 if score1 > 0 else 0
            ),
            "travel_minutes_delta": (run2.total_travel_minutes or 0) - (run1.total_travel_minutes or 0),
        },
    }
