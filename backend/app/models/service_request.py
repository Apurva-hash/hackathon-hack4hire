"""ServiceRequest, JobOffer, and TechnicianLocation models."""

from sqlalchemy import (
    Column, String, Text, Integer, Float, Boolean,
    DateTime, ForeignKey, Enum as SQLEnum
)
from sqlalchemy.orm import relationship
import enum

from app.database import Base
from app.models.base import TimestampMixin, generate_uuid


class RequestStatus(str, enum.Enum):
    REQUESTED = "requested"
    MATCHING = "matching"         # Engine is searching for tech
    ASSIGNED = "assigned"         # Offer sent to a tech
    ACCEPTED = "accepted"         # Tech accepted
    EN_ROUTE = "en_route"         # Tech on the way
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ESCALATED = "escalated"       # No tech found, sent to admin


class RequestUrgency(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class OfferStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ServiceRequest(Base, TimestampMixin):
    """Central booking entity (Uber-style service request)."""
    __tablename__ = "service_requests"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    customer_id = Column(String(36), ForeignKey("customers.id"), nullable=False, index=True)
    category_id = Column(String(36), ForeignKey("service_categories.id"), nullable=False, index=True)
    sla_tier_id = Column(String(36), ForeignKey("sla_tiers.id"), nullable=True)
    assigned_technician_id = Column(String(36), ForeignKey("technician_profiles.id"), nullable=True, index=True)

    # Request details
    description = Column(Text, nullable=True)
    address = Column(String(500), nullable=False)
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    urgency = Column(SQLEnum(RequestUrgency), default=RequestUrgency.NORMAL, nullable=False, index=True)

    # Scheduling
    preferred_time_start = Column(DateTime, nullable=True)
    preferred_time_end = Column(DateTime, nullable=True)
    estimated_duration_minutes = Column(Integer, nullable=True)

    # Status
    status = Column(SQLEnum(RequestStatus), default=RequestStatus.REQUESTED, nullable=False, index=True)
    offer_attempt = Column(Integer, default=0, nullable=False)  # How many techs have been tried
    escalated_to_admin = Column(Boolean, default=False, nullable=False)

    # SLA deadlines (computed at booking time)
    sla_response_deadline = Column(DateTime, nullable=True)
    sla_resolution_deadline = Column(DateTime, nullable=True)
    sla_response_met = Column(Boolean, nullable=True)   # null=not yet evaluated
    sla_resolution_met = Column(Boolean, nullable=True)

    # Completion
    completed_at = Column(DateTime, nullable=True)
    completion_notes = Column(Text, nullable=True)
    estimated_price = Column(Float, nullable=True)

    # Relationships
    customer = relationship("Customer", back_populates="service_requests")
    category = relationship("ServiceCategory", back_populates="service_requests")
    sla_tier = relationship("SLATier", back_populates="service_requests")
    assigned_technician = relationship("TechnicianProfile", foreign_keys=[assigned_technician_id])
    offers = relationship("JobOffer", back_populates="service_request", cascade="all, delete-orphan")
    rating = relationship("Rating", back_populates="service_request", uselist=False, cascade="all, delete-orphan")
    sla_events = relationship("SLAEvent", back_populates="service_request", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ServiceRequest(id={self.id}, status={self.status}, urgency={self.urgency})>"


class JobOffer(Base, TimestampMixin):
    """An offer of a ServiceRequest sent to a specific technician."""
    __tablename__ = "job_offers"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    service_request_id = Column(String(36), ForeignKey("service_requests.id"), nullable=False, index=True)
    technician_profile_id = Column(String(36), ForeignKey("technician_profiles.id"), nullable=False, index=True)

    offered_at = Column(DateTime, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    status = Column(SQLEnum(OfferStatus), default=OfferStatus.PENDING, nullable=False, index=True)
    rejection_reason = Column(Text, nullable=True)
    attempt_number = Column(Integer, nullable=False, default=1)

    # Relationships
    service_request = relationship("ServiceRequest", back_populates="offers")
    technician_profile = relationship("TechnicianProfile", back_populates="offers", foreign_keys=[technician_profile_id])

    def __repr__(self):
        return f"<JobOffer(id={self.id}, status={self.status}, attempt={self.attempt_number})>"


class TechnicianLocation(Base):
    """Live location record for a technician (updated on each location ping)."""
    __tablename__ = "technician_locations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    technician_profile_id = Column(String(36), ForeignKey("technician_profiles.id"), nullable=False, unique=True, index=True)
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    technician_profile = relationship("TechnicianProfile", back_populates="location_record")

    def __repr__(self):
        return f"<TechnicianLocation(tech={self.technician_profile_id}, lat={self.lat}, lng={self.lng})>"

