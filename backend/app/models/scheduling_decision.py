"""Scheduling Decision model for explainability."""

from sqlalchemy import Column, String, Text, DateTime, Integer, Float, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum

from app.database import Base
from app.models.base import generate_uuid


class Feasibility(str, enum.Enum):
    """Job feasibility classification."""
    FEASIBLE = "feasible"
    CURRENTLY_INFEASIBLE = "currently_infeasible"
    IMPOSSIBLE = "impossible"


class RejectionReason(str, enum.Enum):
    """Reason codes for unassigned jobs."""
    MISSING_SKILL = "MISSING_SKILL"
    NO_ZONE_ELIGIBILITY = "NO_ZONE_ELIGIBILITY"
    NO_AVAILABLE_SLOT = "NO_AVAILABLE_SLOT"
    SHIFT_CONFLICT = "SHIFT_CONFLICT"
    TRAVEL_CONFLICT = "TRAVEL_CONFLICT"
    SLA_CONFLICT = "SLA_CONFLICT"
    RESOURCE_UNAVAILABLE = "RESOURCE_UNAVAILABLE"
    TIME_WINDOW_CONFLICT = "TIME_WINDOW_CONFLICT"


class SchedulingDecision(Base):
    """Record of a scheduling decision for a job."""
    
    __tablename__ = "scheduling_decisions"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    run_id = Column(String(36), ForeignKey("scheduling_runs.id"), nullable=False, index=True)
    job_id = Column(String(36), ForeignKey("jobs.id"), nullable=False, index=True)
    
    # Assignment details (null if unassigned)
    technician_id = Column(String(36), ForeignKey("technicians.id"), nullable=True)
    scheduled_start = Column(DateTime, nullable=True)
    
    # Feasibility and explanation
    feasibility = Column(SQLEnum(Feasibility), nullable=False)
    rejection_reason = Column(SQLEnum(RejectionReason), nullable=True)
    explanation_text = Column(Text, nullable=True)
    
    # Decision metrics
    candidate_count = Column(Integer, default=0, nullable=False)
    selected_score = Column(Float, nullable=True)
    
    # Relationships
    scheduling_run = relationship("SchedulingRun", back_populates="decisions")
    job = relationship("Job", back_populates="scheduling_decisions")
    
    def __repr__(self):
        return f"<SchedulingDecision(id={self.id}, job_id={self.job_id}, feasibility={self.feasibility})>"
