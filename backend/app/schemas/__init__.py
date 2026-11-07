"""Pydantic schemas for request/response validation."""

from app.schemas.common import MessageResponse, ErrorResponse, TimestampSchema
from app.schemas.skill import SkillCreate, SkillUpdate, SkillResponse
from app.schemas.service_zone import ServiceZoneCreate, ServiceZoneUpdate, ServiceZoneResponse
from app.schemas.job import JobCreate, JobUpdate, JobResponse, JobListResponse
from app.schemas.technician import (
    TechnicianCreate,
    TechnicianUpdate,
    TechnicianResponse,
    TechnicianListResponse,
    AvailabilityBlockCreate,
    AvailabilityBlockResponse,
)

__all__ = [
    "MessageResponse",
    "ErrorResponse",
    "TimestampSchema",
    "SkillCreate",
    "SkillUpdate",
    "SkillResponse",
    "ServiceZoneCreate",
    "ServiceZoneUpdate",
    "ServiceZoneResponse",
    "JobCreate",
    "JobUpdate",
    "JobResponse",
    "JobListResponse",
    "TechnicianCreate",
    "TechnicianUpdate",
    "TechnicianResponse",
    "TechnicianListResponse",
    "AvailabilityBlockCreate",
    "AvailabilityBlockResponse",
]
