"""Technician schemas."""

from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, time
from typing import List, Optional

from app.models.technician import TechnicianStatus


class SkillRef(BaseModel):
    """Skill reference for nested responses."""
    id: str
    name: str
    description: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class ServiceZoneRef(BaseModel):
    """Service zone reference for nested responses."""
    id: str
    name: str
    description: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class TechnicianBase(BaseModel):
    """Base technician schema."""
    name: str = Field(..., min_length=1, max_length=255)
    email: Optional[str] = None
    phone: Optional[str] = None
    current_location: Optional[str] = None
    shift_start: time
    shift_end: time


class TechnicianCreate(TechnicianBase):
    """Schema for creating a technician."""
    skill_ids: List[str] = Field(default_factory=list)
    service_zone_ids: List[str] = Field(default_factory=list)
    # Accept zone_ids as an alias so the frontend can use either name
    zone_ids: Optional[List[str]] = Field(default=None)
    status: TechnicianStatus = TechnicianStatus.AVAILABLE


class TechnicianUpdate(BaseModel):
    """Schema for updating a technician."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[str] = None
    phone: Optional[str] = None
    current_location: Optional[str] = None
    shift_start: Optional[time] = None
    shift_end: Optional[time] = None
    status: Optional[TechnicianStatus] = None
    skill_ids: Optional[List[str]] = None
    service_zone_ids: Optional[List[str]] = None


class TechnicianResponse(TechnicianBase):
    """Schema for technician response."""
    id: str
    status: TechnicianStatus
    created_at: datetime
    updated_at: datetime
    skills: List[SkillRef] = []
    service_zones: List[ServiceZoneRef] = []

    model_config = ConfigDict(from_attributes=True)


class TechnicianListResponse(BaseModel):
    """Schema for technician list response."""
    total: int
    technicians: List[TechnicianResponse]


class AvailabilityBlockCreate(BaseModel):
    """Schema for creating availability block."""
    start_time: datetime
    end_time: datetime
    reason: Optional[str] = None


class AvailabilityBlockResponse(BaseModel):
    """Schema for availability block response."""
    id: str
    technician_id: str
    start_time: datetime
    end_time: datetime
    reason: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
