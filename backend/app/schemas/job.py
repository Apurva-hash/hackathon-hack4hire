"""Job schemas."""

from pydantic import BaseModel, Field, field_validator, ConfigDict, model_validator
from datetime import datetime, timedelta
from typing import List, Optional

from app.models.job import JobPriority, JobStatus


class SkillRef(BaseModel):
    id: str
    name: str
    model_config = ConfigDict(from_attributes=True)


class ServiceZoneRef(BaseModel):
    id: str
    name: str
    model_config = ConfigDict(from_attributes=True)


class AssignmentRef(BaseModel):
    id: str
    technician_id: str
    scheduled_start: datetime
    scheduled_end: datetime
    travel_before_minutes: int = 0
    status: str
    model_config = ConfigDict(from_attributes=True)


class JobBase(BaseModel):
    """Base job schema."""
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    location: str = Field(default="Main Service Area", min_length=1, max_length=255)
    service_zone_id: Optional[str] = None
    duration_minutes: int = Field(default=60, gt=0)
    time_window_start: Optional[datetime] = None
    time_window_end: Optional[datetime] = None
    sla_deadline: Optional[datetime] = None
    priority: JobPriority = JobPriority.MEDIUM

    @model_validator(mode='before')
    @classmethod
    def set_defaults_and_validate(cls, data: dict):
        if not isinstance(data, dict):
            return data
        
        now = datetime.utcnow()
        if not data.get('time_window_start'):
            data['time_window_start'] = now
        elif isinstance(data['time_window_start'], str):
            data['time_window_start'] = datetime.fromisoformat(data['time_window_start'].replace('Z', '+00:00'))

        if not data.get('time_window_end'):
            data['time_window_end'] = data['time_window_start'] + timedelta(hours=4)
        elif isinstance(data['time_window_end'], str):
            data['time_window_end'] = datetime.fromisoformat(data['time_window_end'].replace('Z', '+00:00'))

        if not data.get('sla_deadline'):
            data['sla_deadline'] = data['time_window_end'] + timedelta(hours=2)
        elif isinstance(data['sla_deadline'], str):
            data['sla_deadline'] = datetime.fromisoformat(data['sla_deadline'].replace('Z', '+00:00'))

        if data['time_window_end'] <= data['time_window_start']:
            data['time_window_end'] = data['time_window_start'] + timedelta(hours=4)

        if data['sla_deadline'] <= data['time_window_end']:
            data['sla_deadline'] = data['time_window_end'] + timedelta(hours=2)

        return data


class JobCreate(JobBase):
    """Schema for creating a job."""
    required_skill_ids: List[str] = Field(default_factory=list)


class JobUpdate(BaseModel):
    """Schema for updating a job."""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    location: Optional[str] = Field(None, min_length=1, max_length=255)
    service_zone_id: Optional[str] = None
    duration_minutes: Optional[int] = Field(None, gt=0)
    time_window_start: Optional[datetime] = None
    time_window_end: Optional[datetime] = None
    sla_deadline: Optional[datetime] = None
    priority: Optional[JobPriority] = None
    status: Optional[JobStatus] = None
    required_skill_ids: Optional[List[str]] = None


class JobResponse(JobBase):
    """Schema for job response."""
    id: str
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    required_skills: List[SkillRef] = []
    service_zone: Optional[ServiceZoneRef] = None
    assignment: Optional[AssignmentRef] = None

    model_config = ConfigDict(from_attributes=True)


class JobListResponse(BaseModel):
    """Schema for job list response."""
    total: int
    jobs: List[JobResponse]

