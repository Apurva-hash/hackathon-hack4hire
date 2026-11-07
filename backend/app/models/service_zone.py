"""Service Zone model."""

from sqlalchemy import Column, String, Text
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.base import generate_uuid


class ServiceZone(Base):
    """Geographic service zone."""
    
    __tablename__ = "service_zones"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Relationships
    technicians = relationship(
        "Technician",
        secondary="technician_zones",
        back_populates="service_zones"
    )
    jobs = relationship("Job", back_populates="service_zone")
    
    def __repr__(self):
        return f"<ServiceZone(id={self.id}, name={self.name})>"
