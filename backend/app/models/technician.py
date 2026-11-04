"""Technician model."""

from sqlalchemy import Column, String, Time, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum

from app.database import Base
from app.models.base import TimestampMixin, generate_uuid


class TechnicianStatus(str, enum.Enum):
    """Technician availability status."""
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


class Technician(Base, TimestampMixin):
    """Field service technician."""
    
    __tablename__ = "technicians"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False, index=True)
    email = Column(String(255), nullable=True, unique=True, index=True)
    phone = Column(String(50), nullable=True)
    status = Column(SQLEnum(TechnicianStatus), default=TechnicianStatus.AVAILABLE, nullable=False)
    current_location = Column(String(255), nullable=True)
    shift_start = Column(Time, nullable=False)
    shift_end = Column(Time, nullable=False)
    
    # Relationships
    skills = relationship(
        "Skill",
        secondary="technician_skills",
        back_populates="technicians"
    )
    service_zones = relationship(
        "ServiceZone",
        secondary="technician_zones",
        back_populates="technicians"
    )
    availability_blocks = relationship(
        "AvailabilityBlock",
        back_populates="technician",
        cascade="all, delete-orphan"
    )
    assignments = relationship(
        "Assignment",
        back_populates="technician",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self):
        return f"<Technician(id={self.id}, name={self.name}, status={self.status})>"
