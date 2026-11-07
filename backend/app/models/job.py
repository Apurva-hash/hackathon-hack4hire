"""Job model."""

from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, Enum as SQLEnum, CheckConstraint
from sqlalchemy.orm import relationship
import enum

from app.database import Base
from app.models.base import TimestampMixin, generate_uuid


class JobPriority(str, enum.Enum):
    """Job priority levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class JobStatus(str, enum.Enum):
    """Job status in lifecycle."""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    UNASSIGNED = "unassigned"


class Job(Base, TimestampMixin):
    """Service job to be scheduled."""
    
    __tablename__ = "jobs"
    __table_args__ = (
        CheckConstraint('duration_minutes > 0', name='check_duration_positive'),
        CheckConstraint('time_window_end > time_window_start', name='check_time_window_valid'),
    )
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    location = Column(String(255), nullable=False)
    service_zone_id = Column(String(36), ForeignKey("service_zones.id"), nullable=False)
    
    duration_minutes = Column(Integer, nullable=False)
    time_window_start = Column(DateTime, nullable=False, index=True)
    time_window_end = Column(DateTime, nullable=False)
    sla_deadline = Column(DateTime, nullable=False, index=True)
    
    priority = Column(SQLEnum(JobPriority), default=JobPriority.MEDIUM, nullable=False, index=True)
    status = Column(SQLEnum(JobStatus), default=JobStatus.PENDING, nullable=False, index=True)
    
    # Relationships
    service_zone = relationship("ServiceZone", back_populates="jobs")
    required_skills = relationship(
        "Skill",
        secondary="job_skills",
        back_populates="jobs"
    )
    assignment = relationship(
        "Assignment",
        back_populates="job",
        uselist=False,
        cascade="all, delete-orphan"
    )
    scheduling_decisions = relationship(
        "SchedulingDecision",
        back_populates="job",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self):
        return f"<Job(id={self.id}, title={self.title}, status={self.status}, priority={self.priority})>"
