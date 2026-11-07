"""Assignment model linking jobs to technicians."""

from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Enum as SQLEnum, CheckConstraint
from sqlalchemy.orm import relationship
import enum

from app.database import Base
from app.models.base import TimestampMixin, generate_uuid


class AssignmentStatus(str, enum.Enum):
    """Assignment status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class Assignment(Base, TimestampMixin):
    """Assignment of a job to a technician at a specific time."""
    
    __tablename__ = "assignments"
    __table_args__ = (
        CheckConstraint('scheduled_end > scheduled_start', name='check_assignment_time_valid'),
    )
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    job_id = Column(String(36), ForeignKey("jobs.id"), nullable=False, unique=True, index=True)
    technician_id = Column(String(36), ForeignKey("technicians.id"), nullable=False, index=True)
    
    scheduled_start = Column(DateTime, nullable=False, index=True)
    scheduled_end = Column(DateTime, nullable=False, index=True)
    travel_before_minutes = Column(Integer, default=0, nullable=False)
    
    status = Column(SQLEnum(AssignmentStatus), default=AssignmentStatus.PENDING, nullable=False)
    run_id = Column(String(36), ForeignKey("scheduling_runs.id"), nullable=False)
    
    # Relationships
    job = relationship("Job", back_populates="assignment")
    technician = relationship("Technician", back_populates="assignments")
    scheduling_run = relationship("SchedulingRun", back_populates="assignments")
    
    def __repr__(self):
        return f"<Assignment(id={self.id}, job_id={self.job_id}, technician_id={self.technician_id}, status={self.status})>"
