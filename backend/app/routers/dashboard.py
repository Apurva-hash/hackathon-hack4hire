"""
Dashboard Analytics API Router
Provides overview, schedule view, technician workload, and performance KPIs.
"""

from typing import List, Optional
from datetime import datetime, date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from app.database import get_db
from app.models import (
    Job, Technician, Assignment, SchedulingRun, SchedulingDecision,
    JobStatus, JobPriority, AssignmentStatus, TechnicianStatus,
    RunStatus
)
from app.models.assignment import Assignment
from app.schemas.dashboard import (
    DashboardOverview, JobStatusCount, PriorityCount,
    ScheduleAssignmentItem, TechnicianWorkload,
    PerformanceKPIs, UnassignedJobSummary, Alert,
)
from app.models.base import generate_uuid

router = APIRouter(tags=["Dashboard"])


def _isostr(dt) -> Optional[str]:
    """Safe datetime to ISO string."""
    return dt.isoformat() if dt else None


# ====================== Endpoints ======================

@router.get("/overview", response_model=DashboardOverview)
def get_overview(db: Session = Depends(get_db)):
    """
    Overall system statistics:
    - Jobs by status and priority
    - Coverage percentage
    - SLA at-risk count
    - Latest scheduling run summary
    """
    total_jobs = db.query(Job).count()
    total_technicians = db.query(Technician).count()
    total_assignments = db.query(Assignment).count()

    # Jobs by status
    status_counts = []
    for status in JobStatus:
        cnt = db.query(Job).filter(Job.status == status).count()
        status_counts.append(JobStatusCount(status=status.value, count=cnt))

    # Jobs by priority
    priority_counts = []
    for priority in JobPriority:
        total_p = db.query(Job).filter(Job.priority == priority).count()
        assigned_p = (
            db.query(Job)
            .filter(
                Job.priority == priority,
                Job.status.in_([JobStatus.ASSIGNED, JobStatus.IN_PROGRESS, JobStatus.COMPLETED]),
            )
            .count()
        )
        priority_counts.append(
            PriorityCount(
                priority=priority.value,
                count=total_p,
                assigned=assigned_p,
                unassigned=total_p - assigned_p,
            )
        )

    # Coverage percentage
    assigned_jobs = (
        db.query(Job)
        .filter(Job.status.in_([JobStatus.ASSIGNED, JobStatus.IN_PROGRESS, JobStatus.COMPLETED]))
        .count()
    )
    coverage_pct = (assigned_jobs / total_jobs * 100) if total_jobs > 0 else 0.0

    # SLA at-risk: pending/unassigned jobs whose SLA deadline is within 2 hours
    now = datetime.utcnow()
    sla_threshold = now + timedelta(hours=2)
    sla_at_risk = (
        db.query(Job)
        .filter(
            Job.status.in_([JobStatus.PENDING, JobStatus.UNASSIGNED]),
            Job.sla_deadline <= sla_threshold,
        )
        .count()
    )

    # Latest scheduling run
    last_run = (
        db.query(SchedulingRun)
        .filter(SchedulingRun.status == RunStatus.COMPLETED)
        .order_by(SchedulingRun.timestamp.desc())
        .first()
    )

    return DashboardOverview(
        total_jobs=total_jobs,
        total_technicians=total_technicians,
        total_assignments=total_assignments,
        jobs_by_status=status_counts,
        jobs_by_priority=priority_counts,
        coverage_pct=round(coverage_pct, 2),
        sla_at_risk_count=sla_at_risk,
        last_run_id=last_run.id if last_run else None,
        last_run_timestamp=_isostr(last_run.timestamp) if last_run else None,
        last_run_score=last_run.objective_score if last_run else None,
    )


@router.get("/schedule", response_model=List[ScheduleAssignmentItem])
def get_schedule(
    target_date: Optional[date] = Query(None, description="YYYY-MM-DD; defaults to today"),
    db: Session = Depends(get_db),
):
    """
    Today's (or a specific date's) full schedule with all assignments,
    including job and technician details.
    """
    if target_date is None:
        target_date = date.today()

    day_start = datetime.combine(target_date, datetime.min.time())
    day_end = datetime.combine(target_date, datetime.max.time())

    assignments = (
        db.query(Assignment)
        .options(
            joinedload(Assignment.job).joinedload(Job.service_zone),
            joinedload(Assignment.technician),
        )
        .filter(
            Assignment.scheduled_start >= day_start,
            Assignment.scheduled_start <= day_end,
        )
        .order_by(Assignment.scheduled_start)
        .all()
    )

    items = []
    for a in assignments:
        job = a.job
        tech = a.technician
        items.append(
            ScheduleAssignmentItem(
                assignment_id=a.id,
                job_id=a.job_id,
                job_title=job.title if job else "Unknown",
                job_location=job.location if job else "",
                job_priority=job.priority.value if job and job.priority else "medium",
                technician_id=a.technician_id,
                technician_name=tech.name if tech else "Unknown",
                scheduled_start=_isostr(a.scheduled_start),
                scheduled_end=_isostr(a.scheduled_end),
                travel_before_minutes=a.travel_before_minutes,
                status=a.status.value if a.status else "pending",
            )
        )

    return items


@router.get("/technicians", response_model=List[TechnicianWorkload])
def get_technician_workload(
    target_date: Optional[date] = Query(None, description="YYYY-MM-DD; defaults to today"),
    db: Session = Depends(get_db),
):
    """
    Technician workload and status overview for a given day.
    """
    if target_date is None:
        target_date = date.today()

    day_start = datetime.combine(target_date, datetime.min.time())
    day_end = datetime.combine(target_date, datetime.max.time())

    technicians = (
        db.query(Technician)
        .options(joinedload(Technician.assignments))
        .all()
    )

    results = []
    now = datetime.utcnow()

    for tech in technicians:
        # Assignments for the target day
        day_assignments = [
            a for a in tech.assignments
            if a.scheduled_start and day_start <= a.scheduled_start <= day_end
        ]

        total_scheduled_minutes = sum(
            int((a.scheduled_end - a.scheduled_start).total_seconds() / 60)
            for a in day_assignments
            if a.scheduled_start and a.scheduled_end
        )

        # Shift duration in minutes
        shift_start_dt = datetime.combine(target_date, tech.shift_start)
        shift_end_dt = datetime.combine(target_date, tech.shift_end)
        shift_minutes = int((shift_end_dt - shift_start_dt).total_seconds() / 60)

        utilization_pct = (
            (total_scheduled_minutes / shift_minutes * 100) if shift_minutes > 0 else 0.0
        )

        # Next upcoming job
        future_assignments = sorted(
            [a for a in day_assignments if a.scheduled_start and a.scheduled_start >= now],
            key=lambda a: a.scheduled_start,
        )
        next_job_start = _isostr(future_assignments[0].scheduled_start) if future_assignments else None

        results.append(
            TechnicianWorkload(
                technician_id=tech.id,
                technician_name=tech.name,
                status=tech.status.value if tech.status else "available",
                assignments_today=len(day_assignments),
                total_scheduled_minutes=total_scheduled_minutes,
                utilization_pct=round(utilization_pct, 2),
                next_job_start=next_job_start,
            )
        )

    # Sort by utilization descending
    results.sort(key=lambda x: x.utilization_pct, reverse=True)
    return results


@router.get("/performance", response_model=PerformanceKPIs)
def get_performance(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """
    Performance metrics and KPIs derived from past scheduling runs.
    """
    runs = (
        db.query(SchedulingRun)
        .filter(SchedulingRun.status == RunStatus.COMPLETED)
        .order_by(SchedulingRun.timestamp.desc())
        .limit(limit)
        .all()
    )

    total_runs = db.query(SchedulingRun).filter(SchedulingRun.status == RunStatus.COMPLETED).count()

    if not runs:
        return PerformanceKPIs(
            total_scheduling_runs=0,
            avg_objective_score=None,
            avg_sla_violations=None,
            avg_travel_minutes=None,
            best_run_id=None,
            best_score=None,
        )

    scores = [r.objective_score for r in runs if r.objective_score is not None]
    sla_viol = [r.sla_violations for r in runs if r.sla_violations is not None]
    travel = [r.total_travel_minutes for r in runs if r.total_travel_minutes is not None]

    avg_score = sum(scores) / len(scores) if scores else None
    avg_sla = sum(sla_viol) / len(sla_viol) if sla_viol else None
    avg_travel = sum(travel) / len(travel) if travel else None

    best_run = max(runs, key=lambda r: r.objective_score or 0.0) if runs else None

    recent = [
        {
            "id": r.id,
            "timestamp": _isostr(r.timestamp),
            "algorithm_used": r.algorithm_used,
            "objective_score": r.objective_score,
            "sla_violations": r.sla_violations,
            "total_travel_minutes": r.total_travel_minutes,
            "status": r.status.value if r.status else "unknown",
        }
        for r in runs
    ]

    return PerformanceKPIs(
        total_scheduling_runs=total_runs,
        avg_objective_score=round(avg_score, 2) if avg_score is not None else None,
        avg_sla_violations=round(avg_sla, 2) if avg_sla is not None else None,
        avg_travel_minutes=round(avg_travel, 2) if avg_travel is not None else None,
        best_run_id=best_run.id if best_run else None,
        best_score=best_run.objective_score if best_run else None,
        recent_runs=recent,
    )


@router.get("/jobs/unassigned", response_model=List[UnassignedJobSummary])
def get_unassigned_jobs(
    priority: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Summary of all unassigned/pending jobs, including SLA risk flag.
    """
    now = datetime.utcnow()
    sla_threshold = now + timedelta(hours=4)

    query = db.query(Job).filter(Job.status.in_([JobStatus.PENDING, JobStatus.UNASSIGNED]))

    if priority:
        try:
            query = query.filter(Job.priority == JobPriority(priority))
        except ValueError:
            pass

    jobs = query.order_by(Job.sla_deadline).all()

    results = []
    for job in jobs:
        sla_at_risk = job.sla_deadline <= sla_threshold
        results.append(
            UnassignedJobSummary(
                job_id=job.id,
                title=job.title,
                location=job.location,
                priority=job.priority.value if job.priority else "medium",
                status=job.status.value if job.status else "pending",
                time_window_start=_isostr(job.time_window_start),
                time_window_end=_isostr(job.time_window_end),
                sla_deadline=_isostr(job.sla_deadline),
                sla_at_risk=sla_at_risk,
            )
        )

    return results


@router.get("/alerts", response_model=List[Alert])
def get_alerts(db: Session = Depends(get_db)):
    """
    Active system alerts:
    - SLA at-risk (unassigned jobs with deadline within 4 hours)
    - Unassigned critical/high priority jobs
    - Technicians with no assignments today
    """
    now = datetime.utcnow()
    sla_threshold = now + timedelta(hours=4)
    alerts: List[Alert] = []
    alert_idx = 0

    # --- SLA at-risk alerts ---
    sla_risk_jobs = (
        db.query(Job)
        .filter(
            Job.status.in_([JobStatus.PENDING, JobStatus.UNASSIGNED]),
            Job.sla_deadline <= sla_threshold,
        )
        .order_by(Job.sla_deadline)
        .all()
    )
    for job in sla_risk_jobs:
        minutes_left = int((job.sla_deadline - now).total_seconds() / 60)
        severity = "critical" if minutes_left < 60 else "warning"
        alert_idx += 1
        alerts.append(
            Alert(
                alert_id=f"sla-{job.id}",
                severity=severity,
                category="sla",
                message=(
                    f"Job '{job.title}' [{job.priority.value}] SLA deadline in "
                    f"{minutes_left} min — not yet assigned"
                ),
                entity_id=job.id,
                entity_type="job",
                created_at=_isostr(now),
            )
        )

    # --- Unassigned critical jobs ---
    critical_unassigned = (
        db.query(Job)
        .filter(
            Job.priority == JobPriority.CRITICAL,
            Job.status.in_([JobStatus.PENDING, JobStatus.UNASSIGNED]),
        )
        .all()
    )
    for job in critical_unassigned:
        # Avoid duplicate if already flagged in SLA alerts
        if not any(a.entity_id == job.id for a in alerts):
            alerts.append(
                Alert(
                    alert_id=f"unassigned-critical-{job.id}",
                    severity="critical",
                    category="unassigned",
                    message=f"CRITICAL priority job '{job.title}' is unassigned",
                    entity_id=job.id,
                    entity_type="job",
                    created_at=_isostr(now),
                )
            )

    # --- Unassigned HIGH priority jobs ---
    high_unassigned = (
        db.query(Job)
        .filter(
            Job.priority == JobPriority.HIGH,
            Job.status.in_([JobStatus.PENDING, JobStatus.UNASSIGNED]),
        )
        .limit(10)
        .all()
    )
    for job in high_unassigned:
        if not any(a.entity_id == job.id for a in alerts):
            alerts.append(
                Alert(
                    alert_id=f"unassigned-high-{job.id}",
                    severity="warning",
                    category="unassigned",
                    message=f"HIGH priority job '{job.title}' is unassigned",
                    entity_id=job.id,
                    entity_type="job",
                    created_at=_isostr(now),
                )
            )

    # --- Idle technicians (no assignments today) ---
    today_start = datetime.combine(now.date(), datetime.min.time())
    today_end = datetime.combine(now.date(), datetime.max.time())

    all_techs = db.query(Technician).filter(
        Technician.status == TechnicianStatus.AVAILABLE
    ).all()

    for tech in all_techs:
        today_count = (
            db.query(Assignment)
            .filter(
                Assignment.technician_id == tech.id,
                Assignment.scheduled_start >= today_start,
                Assignment.scheduled_start <= today_end,
            )
            .count()
        )
        if today_count == 0:
            alerts.append(
                Alert(
                    alert_id=f"idle-tech-{tech.id}",
                    severity="info",
                    category="technician",
                    message=f"Technician '{tech.name}' has no assignments today",
                    entity_id=tech.id,
                    entity_type="technician",
                    created_at=_isostr(now),
                )
            )

    return alerts
