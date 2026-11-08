"""Payment and Revenue Sharing model for DispatchGrid."""

from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum
from datetime import datetime

from app.database import Base
from app.models.base import TimestampMixin, generate_uuid


class PaymentMethod(str, enum.Enum):
    CASH = "cash"
    GPAY = "gpay"
    PHONEPE = "phonepe"


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class Payment(Base, TimestampMixin):
    """Payment record storing transaction details and 40%/60% revenue split."""
    __tablename__ = "payments"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    service_request_id = Column(String(36), ForeignKey("service_requests.id"), nullable=False, index=True)
    customer_id = Column(String(36), ForeignKey("customers.id"), nullable=False, index=True)
    technician_profile_id = Column(String(36), ForeignKey("technician_profiles.id"), nullable=True, index=True)

    amount = Column(Float, nullable=False, default=0.0)
    admin_share = Column(Float, nullable=False, default=0.0)       # 40% Admin Share
    technician_share = Column(Float, nullable=False, default=0.0)  # 60% Technician Share

    payment_method = Column(SQLEnum(PaymentMethod), nullable=False, default=PaymentMethod.CASH)
    status = Column(SQLEnum(PaymentStatus), nullable=False, default=PaymentStatus.PENDING, index=True)

    transaction_id = Column(String(100), nullable=True, unique=True, index=True)
    failure_reason = Column(String(255), nullable=True)
    paid_at = Column(DateTime, nullable=True)

    # Relationships
    service_request = relationship("ServiceRequest", backref="payments")
    customer = relationship("Customer", backref="payments")
    technician_profile = relationship("TechnicianProfile", backref="payments")

    def __repr__(self):
        return f"<Payment(id={self.id}, amount={self.amount}, method={self.payment_method}, status={self.status})>"
