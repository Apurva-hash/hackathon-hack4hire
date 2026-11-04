"""Notification model."""

from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum

from app.database import Base
from app.models.base import TimestampMixin, generate_uuid


class NotificationType(str, enum.Enum):
    JOB_ASSIGNED = "job_assigned"
    OFFER_RECEIVED = "offer_received"
    OFFER_ACCEPTED = "offer_accepted"
    OFFER_REJECTED = "offer_rejected"
    STATUS_CHANGED = "status_changed"
    SLA_AT_RISK = "sla_at_risk"
    SLA_BREACHED = "sla_breached"
    JOB_COMPLETED = "job_completed"
    JOB_CANCELLED = "job_cancelled"
    NEW_RATING = "new_rating"
    ADMIN_ACTION = "admin_action"
    SYSTEM = "system"


class Notification(Base, TimestampMixin):
    """In-app notification record."""
    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    type = Column(SQLEnum(NotificationType), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=True)
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    entity_type = Column(String(50), nullable=True)   # e.g. "service_request"
    entity_id = Column(String(36), nullable=True)

    user = relationship("User", back_populates="notifications")

    def __repr__(self):
        return f"<Notification(type={self.type}, user={self.user_id}, read={self.is_read})>"

