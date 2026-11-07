"""Schemas for Disruption endpoints."""

from typing import Optional, Any, Dict
from datetime import datetime
from pydantic import BaseModel, ConfigDict, field_validator


class DisruptionCreate(BaseModel):
    event_type: str  # DisruptionEventType value
    affected_entity_type: str  # "technician" or "job"
    affected_entity_id: str
    event_time: Optional[datetime] = None
    payload: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "event_type": "technician_unavailable",
                "affected_entity_type": "technician",
                "affected_entity_id": "uuid-here",
                "payload": {"reason": "sick leave", "until": "2026-10-31T17:00:00"},
            }
        }
    )


class DisruptionOut(BaseModel):
    id: str
    event_type: str
    affected_entity_type: str
    affected_entity_id: str
    event_time: datetime
    payload: Optional[str] = None   # stored as JSON text
    processed_run_id: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("event_type", mode="before")
    @classmethod
    def coerce_event_type(cls, v):
        """Convert enum to string value."""
        return v.value if hasattr(v, "value") else str(v)


class DisruptionProcessResult(BaseModel):
    disruption_id: str
    run_id: Optional[str] = None
    status: str
    message: str
    jobs_reassigned: int = 0
    jobs_unassigned: int = 0

