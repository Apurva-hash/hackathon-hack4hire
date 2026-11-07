"""Skill model."""

from sqlalchemy import Column, String, Text
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.base import generate_uuid


class Skill(Base):
    """Skill that technicians can possess and jobs can require."""
    
    __tablename__ = "skills"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Relationships
    technicians = relationship(
        "Technician",
        secondary="technician_skills",
        back_populates="skills"
    )
    jobs = relationship(
        "Job",
        secondary="job_skills",
        back_populates="required_skills"
    )
    
    def __repr__(self):
        return f"<Skill(id={self.id}, name={self.name})>"
