"""Availability Block model for technician unavailable periods."""

from sqlalchemy import Column, String, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.base import TimestampMixin, generate_uuid


class AvailabilityBlock(Base, TimestampMixin):
    """Period when a technician is unavailable."""
    
    __tablename__ = "availability_blocks"
    __table_args__ = (
        CheckConstraint('end_time > start_time', name='check_availability_time_valid'),
    )
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    technician_id = Column(String(36), ForeignKey("technicians.id"), nullable=False, index=True)
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=False, index=True)
    reason = Column(String(255), nullable=True)
    
    # Relationships
    technician = relationship("Technician", back_populates="availability_blocks")
    
    def __repr__(self):
        return f"<AvailabilityBlock(id={self.id}, technician_id={self.technician_id}, start={self.start_time}, end={self.end_time})>"
