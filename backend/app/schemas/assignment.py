"""Schemas for Assignment endpoints."""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class AssignmentBase(BaseModel):
    job_id: str
    technician_id: str
    scheduled_start: datetime
    scheduled_end: datetime
    travel_before_minutes: int = 0
    status: str = "pending"
    run_id: Optional[str] = None


class AssignmentCreate(AssignmentBase):
    pass


class AssignmentUpdate(BaseModel):
    status: Optional[str] = None
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    travel_before_minutes: Optional[int] = None


class AssignmentOut(AssignmentBase):
    id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AssignmentDetail(AssignmentOut):
    """Full assignment with nested job/technician info."""
    job_title: Optional[str] = None
    job_location: Optional[str] = None
    job_priority: Optional[str] = None
    technician_name: Optional[str] = None

