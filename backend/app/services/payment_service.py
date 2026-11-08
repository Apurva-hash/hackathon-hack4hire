"""Payment and Revenue Sharing Service for DispatchGrid.

Handles:
- Demo payment processing (Cash on Delivery, Google Pay, PhonePe)
- Realistic transaction ID generation
- 40% Admin / 60% Technician revenue sharing calculations
- Idempotent earnings credit preventing duplicate calculations
"""

from __future__ import annotations

import logging
import random
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models import (
    ServiceRequest,
    Customer,
    TechnicianProfile,
    Payment,
    PaymentMethod,
    PaymentStatus,
    RequestStatus,
    Notification,
    NotificationType,
)
from app.models.base import generate_uuid

logger = logging.getLogger(__name__)


def generate_transaction_id(method: PaymentMethod) -> str:
    """Generate a realistic UPI / COD transaction ID."""
    now_str = datetime.utcnow().strftime("%Y%m%d%H%M")
    rand_suffix = "".join(random.choices("0123456789", k=8))
    if method == PaymentMethod.GPAY:
        return f"UPI-GPAY-{now_str}-{rand_suffix}"
    elif method == PaymentMethod.PHONEPE:
        return f"UPI-PHONEPE-{now_str}-{rand_suffix}"
    else:
        return f"COD-{now_str}-{rand_suffix}"


def settle_revenue(db: Session, sr: ServiceRequest) -> None:
    """Idempotently credit technician share when booking is completed and paid."""
    if sr.status != RequestStatus.COMPLETED:
        return

    # Find successful payment
    payment = (
        db.query(Payment)
        .filter(
            Payment.service_request_id == sr.id,
            Payment.status == PaymentStatus.COMPLETED,
        )
        .first()
    )
    if not payment:
        return

    # Update payment technician link if not set
    if not payment.technician_profile_id and sr.assigned_technician_id:
        payment.technician_profile_id = sr.assigned_technician_id

    # Recalculate technician total earnings from ALL completed and paid jobs
    # This strictly guarantees NO duplicate calculations or inflation!
    if payment.technician_profile_id:
        tech = db.query(TechnicianProfile).filter(TechnicianProfile.id == payment.technician_profile_id).first()
        if tech:
            total_tech_earnings = (
                db.query(Payment)
                .join(ServiceRequest, Payment.service_request_id == ServiceRequest.id)
                .filter(
                    Payment.technician_profile_id == tech.id,
                    Payment.status == PaymentStatus.COMPLETED,
                    ServiceRequest.status == RequestStatus.COMPLETED,
                )
                .all()
            )
            # Sum of 60% shares
            tech.total_earnings = round(sum(p.technician_share for p in total_tech_earnings), 2)
            db.commit()
            logger.info("Technician %s total earnings recalculated: ₹%s", tech.id, tech.total_earnings)


def process_payment(
    db: Session,
    service_request_id: str,
    customer_id: str,
    method: str,
    simulate_status: str = "success",
) -> dict:
    """Process demo customer payment with 40/60 revenue split."""
    sr = db.query(ServiceRequest).filter(ServiceRequest.id == service_request_id).first()
    if not sr:
        raise ValueError("Service request not found")

    amount = sr.estimated_price if (sr.estimated_price and sr.estimated_price > 0) else 500.0
    admin_share = round(amount * 0.40, 2)
    technician_share = round(amount * 0.60, 2)

    # Normalize method
    method_lower = method.lower().strip()
    if method_lower in ("gpay", "google_pay", "google pay"):
        pay_method = PaymentMethod.GPAY
    elif method_lower in ("phonepe", "phone_pe"):
        pay_method = PaymentMethod.PHONEPE
    elif method_lower in ("cash", "cod", "cash_on_delivery"):
        pay_method = PaymentMethod.CASH
    else:
        raise ValueError(f"Unsupported payment method: {method}")

    # Check for existing completed payment to prevent duplicates
    existing_completed = (
        db.query(Payment)
        .filter(
            Payment.service_request_id == sr.id,
            Payment.status == PaymentStatus.COMPLETED,
        )
        .first()
    )
    if existing_completed:
        return {
            "payment_id": existing_completed.id,
            "status": "completed",
            "message": "Payment already completed for this booking",
            "transaction_id": existing_completed.transaction_id,
            "amount": existing_completed.amount,
            "admin_share": existing_completed.admin_share,
            "technician_share": existing_completed.technician_share,
            "payment_method": existing_completed.payment_method.value,
            "paid_at": existing_completed.paid_at.isoformat() if existing_completed.paid_at else None,
        }

    # Find existing pending or failed payment to reuse or create new
    payment = (
        db.query(Payment)
        .filter(Payment.service_request_id == sr.id)
        .order_by(Payment.created_at.desc())
        .first()
    )

    if not payment:
        payment = Payment(
            id=generate_uuid(),
            service_request_id=sr.id,
            customer_id=customer_id,
            technician_profile_id=sr.assigned_technician_id,
            amount=amount,
            admin_share=admin_share,
            technician_share=technician_share,
            payment_method=pay_method,
            status=PaymentStatus.PENDING,
        )
        db.add(payment)
    else:
        payment.payment_method = pay_method
        payment.amount = amount
        payment.admin_share = admin_share
        payment.technician_share = technician_share
        if sr.assigned_technician_id:
            payment.technician_profile_id = sr.assigned_technician_id

    # Handle Cash vs Online
    if pay_method == PaymentMethod.CASH:
        payment.status = PaymentStatus.PENDING
        payment.transaction_id = f"COD-PENDING-{sr.id[:8].upper()}"
        payment.failure_reason = None
        db.commit()
        db.refresh(payment)
        return {
            "payment_id": payment.id,
            "status": "pending",
            "payment_method": "cash",
            "message": "Cash on Delivery selected. Pay cash directly to technician upon job completion.",
            "transaction_id": payment.transaction_id,
            "amount": amount,
            "admin_share": admin_share,
            "technician_share": technician_share,
        }

    # Online Payments (GPay or PhonePe)
    if simulate_status == "failed":
        payment.status = PaymentStatus.FAILED
        payment.transaction_id = generate_transaction_id(pay_method)
        payment.failure_reason = "Simulated bank payment failure: Issuer bank timeout / UPI declined"
        db.commit()
        db.refresh(payment)
        return {
            "payment_id": payment.id,
            "status": "failed",
            "payment_method": pay_method.value,
            "message": payment.failure_reason,
            "transaction_id": payment.transaction_id,
            "amount": amount,
        }

    # Simulate success
    payment.status = PaymentStatus.COMPLETED
    payment.paid_at = datetime.utcnow()
    payment.transaction_id = generate_transaction_id(pay_method)
    payment.failure_reason = None

    db.commit()
    db.refresh(payment)

    # Settle revenue if job is completed
    settle_revenue(db, sr)

    # Send confirmation notification
    cust = db.query(Customer).filter(Customer.id == customer_id).first()
    if cust:
        notif = Notification(
            user_id=cust.user_id,
            type=NotificationType.STATUS_CHANGED,
            title="Payment Successful",
            body=f"Payment of ₹{amount} via {pay_method.value.upper()} received. Ref: {payment.transaction_id}",
            entity_type="service_request",
            entity_id=sr.id,
        )
        db.add(notif)
        db.commit()

    return {
        "payment_id": payment.id,
        "status": "completed",
        "payment_method": pay_method.value,
        "message": f"Demo payment of ₹{amount} processed successfully via {pay_method.value.upper()}!",
        "transaction_id": payment.transaction_id,
        "amount": amount,
        "admin_share": admin_share,
        "technician_share": technician_share,
        "paid_at": payment.paid_at.isoformat() if payment.paid_at else None,
    }
