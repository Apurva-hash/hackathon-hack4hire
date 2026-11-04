"""User, Customer, and TechnicianProfile models for auth and roles."""

from sqlalchemy import (
    Column, String, Text, Boolean, Integer, Float,
    ForeignKey, Enum as SQLEnum, JSON
)
from sqlalchemy.orm import relationship
import enum

from app.database import Base
from app.models.base import TimestampMixin, generate_uuid


class UserRole(str, enum.Enum):
    CUSTOMER = "customer"
    TECHNICIAN = "technician"
    ADMIN = "admin"


class User(Base, TimestampMixin):
    """Base authentication user."""
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), nullable=False, unique=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    customer_profile = relationship("Customer", back_populates="user", uselist=False, cascade="all, delete-orphan")
    technician_profile = relationship("TechnicianProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"


class Customer(Base, TimestampMixin):
    """Customer profile linked to User."""
    __tablename__ = "customers"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=True)
    avg_rating = Column(Float, default=0.0, nullable=False)
    total_bookings = Column(Integer, default=0, nullable=False)
    # Saved addresses as JSON list: [{label, address, lat, lng}]
    saved_addresses = Column(JSON, default=list, nullable=False)

    # Relationships
    user = relationship("User", back_populates="customer_profile")
    service_requests = relationship("ServiceRequest", back_populates="customer", cascade="all, delete-orphan")
    ratings_given = relationship("Rating", back_populates="customer", foreign_keys="Rating.customer_id")

    def __repr__(self):
        return f"<Customer(id={self.id}, name={self.name})>"


class TechnicianProfile(Base, TimestampMixin):
    """Extended profile for technician users, linked to existing Technician model."""
    __tablename__ = "technician_profiles"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, unique=True, index=True)
    # Link to existing Technician (optional, for orgs using Phase 1-7 scheduling)
    technician_id = Column(String(36), ForeignKey("technicians.id"), nullable=True, unique=True)

    name = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=True)
    bio = Column(Text, nullable=True)

    # Location & availability
    is_online = Column(Boolean, default=False, nullable=False, index=True)
    is_approved = Column(Boolean, default=False, nullable=False, index=True)
    is_suspended = Column(Boolean, default=False, nullable=False)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    service_radius_km = Column(Float, default=15.0, nullable=False)
    max_concurrent_jobs = Column(Integer, default=3, nullable=False)

    # Skill level / certification (1-5 scale)
    certification_level = Column(Integer, default=1, nullable=False)

    # Performance metrics
    avg_rating = Column(Float, default=0.0, nullable=False)
    total_jobs_completed = Column(Integer, default=0, nullable=False)
    total_jobs_rejected = Column(Integer, default=0, nullable=False)
    acceptance_rate = Column(Float, default=1.0, nullable=False)  # 0.0 – 1.0
    total_earnings = Column(Float, default=0.0, nullable=False)

    # Relationships
    user = relationship("User", back_populates="technician_profile")
    technician = relationship("Technician", foreign_keys=[technician_id])
    offers = relationship("JobOffer", back_populates="technician_profile", foreign_keys="JobOffer.technician_profile_id")
    location_record = relationship("TechnicianLocation", back_populates="technician_profile", uselist=False, cascade="all, delete-orphan")
    ratings_received = relationship("Rating", back_populates="technician", foreign_keys="Rating.technician_profile_id")

    def __repr__(self):
        return f"<TechnicianProfile(id={self.id}, name={self.name}, online={self.is_online})>"

