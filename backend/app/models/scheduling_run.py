"""Scheduling Run model for audit trail."""

from sqlalchemy import Column, String, Text, DateTime, Float, Integer, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.database import Base
from app.models.base import generate_uuid


class RunStatus(str, enum.Enum):
    """Scheduling run status."""
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TriggerType(str, enum.Enum):
    """Type of trigger that initiated the scheduling run."""
    INITIAL = "initial"
    REOPTIMIZATION = "reoptimization"
    TECHNICIAN_UNAVAILABLE = "technician_unavailable"
    URGENT_JOB = "urgent_job"
    DURATION_CHANGE = "duration_change"
    JOB_CANCELLATION = "job_cancellation"
    EARLY_COMPLETION = "early_completion"
    LATE_COMPLETION = "late_completion"
    MANUAL = "manual"


class SchedulingRun(Base):
    """Record of a scheduling engine execution."""
    
    __tablename__ = "scheduling_runs"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    trigger_type = Column(SQLEnum(TriggerType), nullable=False, index=True)
    trigger_description = Column(Text, nullable=True)
    algorithm_version = Column(String(50), default="1.0.0", nullable=False)
    algorithm_used = Column(String(50), default="auto", nullable=False)
    
    # Metrics
    objective_score = Column(Float, nullable=True)
    total_travel_minutes = Column(Integer, nullable=True)
    sla_violations = Column(Integer, nullable=True)
    unassigned_high_priority = Column(Integer, nullable=True)
    overtime_minutes = Column(Integer, nullable=True)
    assignment_changes = Column(Integer, nullable=True)
    
    status = Column(SQLEnum(RunStatus), default=RunStatus.RUNNING, nullable=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    assignments = relationship("Assignment", back_populates="scheduling_run")
    decisions = relationship(
        "SchedulingDecision",
        back_populates="scheduling_run",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self):
        return f"<SchedulingRun(id={self.id}, trigger={self.trigger_type}, status={self.status})>"
