"""Schemas for Dashboard endpoints."""

from typing import Optional, List, Any, Dict
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class JobStatusCount(BaseModel):
    status: str
    count: int


class PriorityCount(BaseModel):
    priority: str
    count: int
    assigned: int
    unassigned: int


class DashboardOverview(BaseModel):
    total_jobs: int
    total_technicians: int
    total_assignments: int
    jobs_by_status: List[JobStatusCount]
    jobs_by_priority: List[PriorityCount]
    coverage_pct: float
    sla_at_risk_count: int
    last_run_id: Optional[str] = None
    last_run_timestamp: Optional[str] = None
    last_run_score: Optional[float] = None


class ScheduleAssignmentItem(BaseModel):
    assignment_id: str
    job_id: str
    job_title: str
    job_location: str
    job_priority: str
    technician_id: str
    technician_name: str
    scheduled_start: str
    scheduled_end: str
    travel_before_minutes: int
    status: str


class TechnicianWorkload(BaseModel):
    technician_id: str
    technician_name: str
    status: str
    assignments_today: int
    total_scheduled_minutes: int
    utilization_pct: float
    next_job_start: Optional[str] = None


class PerformanceKPIs(BaseModel):
    total_scheduling_runs: int
    avg_objective_score: Optional[float]
    avg_sla_violations: Optional[float]
    avg_travel_minutes: Optional[float]
    best_run_id: Optional[str]
    best_score: Optional[float]
    recent_runs: List[Dict[str, Any]] = []


class UnassignedJobSummary(BaseModel):
    job_id: str
    title: str
    location: str
    priority: str
    status: str
    time_window_start: str
    time_window_end: str
    sla_deadline: str
    sla_at_risk: bool


class Alert(BaseModel):
    alert_id: str
    severity: str  # "critical", "warning", "info"
    category: str  # "sla", "unassigned", "technician"
    message: str
    entity_id: Optional[str] = None
    entity_type: Optional[str] = None
    created_at: str
