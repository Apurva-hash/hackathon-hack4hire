"""SLA Tier and SLA Event models."""

from sqlalchemy import Column, String, Text, Integer, Float, Boolean, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum

from app.database import Base
from app.models.base import TimestampMixin, generate_uuid


class SLATier(Base, TimestampMixin):
    """SLA configuration tiers by priority."""
    __tablename__ = "sla_tiers"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False, unique=True)
    priority_level = Column(Integer, nullable=False, index=True)  # 1=critical, 2=high, 3=normal, 4=low
    response_time_minutes = Column(Integer, nullable=False)        # Time to first accept
    resolution_time_minutes = Column(Integer, nullable=False)      # Time to complete job
    is_default = Column(Boolean, default=False, nullable=False)

    service_requests = relationship("ServiceRequest", back_populates="sla_tier")

    def __repr__(self):
        return f"<SLATier(name={self.name}, priority={self.priority_level})>"


class SLAEventType(str, enum.Enum):
    AT_RISK = "at_risk"
    BREACHED = "breached"
    RESOLVED = "resolved"
    ESCALATED = "escalated"


class SLAEvent(Base, TimestampMixin):
    """Audit trail for SLA events on service requests."""
    __tablename__ = "sla_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    service_request_id = Column(String(36), ForeignKey("service_requests.id"), nullable=False, index=True)
    event_type = Column(SQLEnum(SLAEventType), nullable=False)
    message = Column(Text, nullable=True)
    occurred_at = Column(DateTime, nullable=False)

    service_request = relationship("ServiceRequest", back_populates="sla_events")

