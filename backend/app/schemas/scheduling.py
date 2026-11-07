"""Schemas for Scheduling endpoints (moved from router)."""

from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class SchedulingRequest(BaseModel):
    algorithm: str = "auto"
    use_alns: bool = True
    job_ids: Optional[List[str]] = None
    technician_ids: Optional[List[str]] = None
    trigger_type: str = "initial"
    trigger_description: Optional[str] = None
    max_iterations: Optional[int] = 100
    destroy_size_min: Optional[int] = 5
    destroy_size_max: Optional[int] = 20
    initial_temperature: Optional[float] = 100.0
    cooling_rate: Optional[float] = 0.95
    random_seed: Optional[int] = 42


class AssignmentInSchedule(BaseModel):
    job_id: str
    technician_id: str
    scheduled_start: str
    scheduled_end: str
    travel_before_minutes: int

    model_config = ConfigDict(from_attributes=True)


class MetricsResponse(BaseModel):
    total_score: float
    job_coverage: float
    total_travel_time: float
    total_idle_time: float
    priority_fulfillment_rate: float
    technician_utilization: float = 0.0


class SchedulingResponse(BaseModel):
    run_id: str
    status: str
    algorithm: str
    jobs_count: int
    technicians_count: int
    assigned_count: int
    unassigned_count: int
    execution_time: float
    metrics: MetricsResponse
    assignments: List[AssignmentInSchedule]
    comparison: Optional[dict] = None


class SchedulingRunSummary(BaseModel):
    id: str
    timestamp: Optional[str]
    status: str
    algorithm_used: str
    objective_score: Optional[float]
    total_travel_minutes: Optional[int]
    sla_violations: Optional[int]
    unassigned_high_priority: Optional[int]
    trigger_type: str
