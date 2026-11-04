"""ServiceCategory and MatchingConfig models."""

from sqlalchemy import Column, String, Text, Boolean, Float, ForeignKey, Integer
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.base import TimestampMixin, generate_uuid


class ServiceCategory(Base, TimestampMixin):
    """Appliance/service type that customers can book."""
    __tablename__ = "service_categories"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    icon = Column(String(10), nullable=True)          # emoji or icon code
    skill_id = Column(String(36), ForeignKey("skills.id"), nullable=True)
    price_per_minute = Column(Float, default=2.0, nullable=False)
    required_certification_level = Column(Integer, default=1, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    skill = relationship("Skill")
    service_requests = relationship("ServiceRequest", back_populates="category")

    def __repr__(self):
        return f"<ServiceCategory(id={self.id}, name={self.name})>"


class MatchingConfig(Base):
    """Singleton config for the matching/dispatch engine."""
    __tablename__ = "matching_config"

    id = Column(Integer, primary_key=True, default=1)
    # Scoring weights (must sum to 1 ideally, but engine normalises)
    weight_distance = Column(Float, default=0.35, nullable=False)
    weight_rating = Column(Float, default=0.25, nullable=False)
    weight_workload = Column(Float, default=0.20, nullable=False)
    weight_skill_level = Column(Float, default=0.15, nullable=False)
    weight_acceptance_rate = Column(Float, default=0.05, nullable=False)

    # Offer timing
    offer_timeout_seconds = Column(Integer, default=120, nullable=False)
    max_offer_attempts = Column(Integer, default=5, nullable=False)

    # High-risk job rules
    high_risk_min_certification = Column(Integer, default=3, nullable=False)
    high_risk_wider_radius_km = Column(Float, default=30.0, nullable=False)
    high_risk_offer_timeout_seconds = Column(Integer, default=60, nullable=False)

    def __repr__(self):
        return "<MatchingConfig(singleton)>"

