"""Disruption Event model."""

from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.database import Base
from app.models.base import generate_uuid


class DisruptionEventType(str, enum.Enum):
    """Type of disruption event."""
    TECHNICIAN_UNAVAILABLE = "technician_unavailable"
    URGENT_JOB = "urgent_job"
    DURATION_CHANGE = "duration_change"
    JOB_CANCELLATION = "job_cancellation"
    EARLY_COMPLETION = "early_completion"
    LATE_COMPLETION = "late_completion"


class DisruptionType(str, enum.Enum):
    """Alias for disruption types used in legacy scheduler."""
    TECHNICIAN_UNAVAILABLE = "technician_unavailable"
    JOB_CANCELLED = "job_cancellation"
    EMERGENCY_JOB = "urgent_job"
    SCHEDULE_CONFLICT = "duration_change"


class ImpactLevel(str, enum.Enum):
    """Impact severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class DisruptionEvent(Base):
    """Record of a disruption that triggered re-optimization."""
    
    __tablename__ = "disruption_events"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    event_type = Column(SQLEnum(DisruptionEventType), nullable=False, index=True, default=DisruptionEventType.TECHNICIAN_UNAVAILABLE)
    affected_entity_type = Column(String(50), nullable=True, default="technician")  # 'technician' or 'job'
    affected_entity_id = Column(String(36), nullable=True, index=True)
    event_time = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    payload = Column(Text, nullable=True)  # JSON string for additional data
    processed_run_id = Column(String(36), ForeignKey("scheduling_runs.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Legacy alias properties
    @property
    def disruption_type(self):
        return self.event_type

    # Relationships
    processing_run = relationship("SchedulingRun", foreign_keys=[processed_run_id])
    
    def __repr__(self):
        return f"<DisruptionEvent(id={self.id}, type={self.event_type}, entity={self.affected_entity_type}:{self.affected_entity_id})>"
