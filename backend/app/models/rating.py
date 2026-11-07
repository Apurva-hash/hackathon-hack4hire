"""Rating and AuditLog models."""

from sqlalchemy import Column, String, Text, Integer, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.base import TimestampMixin, generate_uuid


class Rating(Base, TimestampMixin):
    """Customer rating + feedback after a service request completes."""
    __tablename__ = "ratings"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    service_request_id = Column(String(36), ForeignKey("service_requests.id"), nullable=False, unique=True, index=True)
    customer_id = Column(String(36), ForeignKey("customers.id"), nullable=False, index=True)
    technician_profile_id = Column(String(36), ForeignKey("technician_profiles.id"), nullable=False, index=True)

    score = Column(Float, nullable=False)   # 1.0 – 5.0
    feedback_text = Column(Text, nullable=True)

    service_request = relationship("ServiceRequest", back_populates="rating")
    customer = relationship("Customer", back_populates="ratings_given", foreign_keys=[customer_id])
    technician = relationship("TechnicianProfile", back_populates="ratings_received", foreign_keys=[technician_profile_id])

    def __repr__(self):
        return f"<Rating(score={self.score}, sr={self.service_request_id})>"


class AuditLog(Base):
    """Immutable audit trail for all admin actions."""
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    admin_user_id = Column(String(36), ForeignKey("users.id"), nullable=True)   # null = system action
    action = Column(String(100), nullable=False, index=True)
    entity_type = Column(String(100), nullable=False, index=True)
    entity_id = Column(String(36), nullable=True, index=True)
    old_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    occurred_at = Column(DateTime, nullable=False, index=True)

    admin_user = relationship("User", foreign_keys=[admin_user_id])

    def __repr__(self):
        return f"<AuditLog(action={self.action}, entity={self.entity_type}/{self.entity_id})>"

