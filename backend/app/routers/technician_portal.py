"""Technician portal API router.

All endpoints require a valid JWT with role=technician.
Prefix: /api/technician
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_technician
from app.models import (
    User, TechnicianProfile, TechnicianLocation, ServiceRequest,
    JobOffer, Rating, Notification,
    RequestStatus, OfferStatus, NotificationType,
)
from app.models.base import generate_uuid
from app.services.matching_service import handle_acceptance, handle_rejection
from app.services.notification_service import notify, mark_read

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Technician"])


# ── Schema helpers ────────────────────────────────────────────────────────────

class AvailabilityUpdate(BaseModel):
    is_online: bool


class LocationUpdate(BaseModel):
    lat: float
    lng: float


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    bio: Optional[str] = None
    service_radius_km: Optional[float] = None
    max_concurrent_jobs: Optional[int] = None


class RejectOfferBody(BaseModel):
    reason: str = Field(..., min_length=1)


class JobStatusUpdate(BaseModel):
    status: str  # en_route | in_progress | completed

class NoteBody(BaseModel):
    note: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_profile(db: Session, user: User) -> TechnicianProfile:
    p = user.technician_profile
    if not p:
        raise HTTPException(status_code=404, detail="Technician profile not found")
    return p


VALID_STATUS_TRANSITIONS: dict[str, str] = {
    "accepted": "en_route",
    "en_route": "in_progress",
    "in_progress": "completed",
}


def _sr_summary(sr: ServiceRequest) -> dict:
    d = {
        "id": sr.id,
        "status": sr.status.value if sr.status else None,
        "urgency": sr.urgency.value if sr.urgency else None,
        "category_id": sr.category_id,
        "category_name": sr.category.name if sr.category else None,
        "description": sr.description,
        "address": sr.address,
        "lat": sr.lat,
        "lng": sr.lng,
        "sla_response_deadline": sr.sla_response_deadline.isoformat() if sr.sla_response_deadline else None,
        "sla_resolution_deadline": sr.sla_resolution_deadline.isoformat() if sr.sla_resolution_deadline else None,
        "estimated_price": sr.estimated_price,
        "completed_at": sr.completed_at.isoformat() if sr.completed_at else None,
        "created_at": sr.created_at.isoformat() if sr.created_at else None,
    }
    if sr.customer:
        d["customer_name"] = sr.customer.name
        d["customer_phone"] = sr.customer.phone
    if hasattr(sr, "payments") and sr.payments:
        latest_payment = sorted(sr.payments, key=lambda p: p.created_at or datetime.min, reverse=True)[0]
        d["payment"] = {
            "id": latest_payment.id,
            "amount": latest_payment.amount,
            "payment_method": latest_payment.payment_method.value if latest_payment.payment_method else None,
            "status": latest_payment.status.value if latest_payment.status else None,
            "transaction_id": latest_payment.transaction_id,
            "technician_share": latest_payment.technician_share,
            "admin_share": latest_payment.admin_share,
        }
    return d


# ── Profile ───────────────────────────────────────────────────────────────────

@router.get("/profile")
def get_profile(current_user: User = Depends(get_current_technician), db: Session = Depends(get_db)):
    p = _get_profile(db, current_user)
    return {
        "id": p.id,
        "user_id": p.user_id,
        "email": current_user.email,
        "name": p.name,
        "phone": p.phone,
        "bio": p.bio,
        "is_online": p.is_online,
        "is_approved": p.is_approved,
        "is_suspended": p.is_suspended,
        "lat": p.lat,
        "lng": p.lng,
        "service_radius_km": p.service_radius_km,
        "max_concurrent_jobs": p.max_concurrent_jobs,
        "certification_level": p.certification_level,
        "avg_rating": p.avg_rating,
        "total_jobs_completed": p.total_jobs_completed,
        "total_jobs_rejected": p.total_jobs_rejected,
        "acceptance_rate": p.acceptance_rate,
        "total_earnings": p.total_earnings,
    }


@router.patch("/profile")
def update_profile(
    body: ProfileUpdate,
    current_user: User = Depends(get_current_technician),
    db: Session = Depends(get_db),
):
    p = _get_profile(db, current_user)
    if body.name is not None:
        p.name = body.name
    if body.phone is not None:
        p.phone = body.phone
    if body.bio is not None:
        p.bio = body.bio
    if body.service_radius_km is not None:
        p.service_radius_km = body.service_radius_km
    if body.max_concurrent_jobs is not None:
        p.max_concurrent_jobs = max(1, body.max_concurrent_jobs)
    db.commit()
    db.refresh(p)
    return {"message": "Profile updated"}


# ── Availability & location ───────────────────────────────────────────────────

@router.patch("/availability")
def set_availability(
    body: AvailabilityUpdate,
    current_user: User = Depends(get_current_technician),
    db: Session = Depends(get_db),
):
    p = _get_profile(db, current_user)
    if not p.is_approved and body.is_online:
        raise HTTPException(status_code=403, detail="Account not yet approved by admin")
    if p.is_suspended:
        raise HTTPException(status_code=403, detail="Account is suspended")
    p.is_online = body.is_online
    db.commit()
    return {"is_online": p.is_online}


@router.patch("/location")
def update_location(
    body: LocationUpdate,
    current_user: User = Depends(get_current_technician),
    db: Session = Depends(get_db),
):
    p = _get_profile(db, current_user)
    # Update profile lat/lng
    p.lat = body.lat
    p.lng = body.lng

    # Upsert TechnicianLocation record
    loc = p.location_record
    if loc is None:
        loc = TechnicianLocation(
            id=generate_uuid(),
            technician_profile_id=p.id,
            lat=body.lat,
            lng=body.lng,
            updated_at=datetime.utcnow(),
        )
        db.add(loc)
    else:
        loc.lat = body.lat
        loc.lng = body.lng
        loc.updated_at = datetime.utcnow()

    db.commit()
    return {"lat": body.lat, "lng": body.lng, "updated_at": loc.updated_at.isoformat()}


# ── Offers ────────────────────────────────────────────────────────────────────

@router.get("/offers")
def list_offers(
    current_user: User = Depends(get_current_technician),
    db: Session = Depends(get_db),
):
    p = _get_profile(db, current_user)
    if not p.is_online or p.is_suspended:
        return {"count": 0, "offers": []}

    now = datetime.utcnow()
    # Filter pending offers and ensure the underlying request has NOT been claimed yet
    offers = (
        db.query(JobOffer)
        .join(ServiceRequest, JobOffer.service_request_id == ServiceRequest.id)
        .filter(
            JobOffer.technician_profile_id == p.id,
            JobOffer.status == OfferStatus.PENDING,
            JobOffer.expires_at > now,
            ServiceRequest.status.in_([RequestStatus.REQUESTED, RequestStatus.MATCHING]),
            ServiceRequest.assigned_technician_id.is_(None),
        )
        .all()
    )
    result = []
    for o in offers:
        sr = o.service_request
        result.append({
            "offer_id": o.id,
            "expires_at": (o.expires_at.isoformat() + "Z") if o.expires_at else None,
            "attempt_number": o.attempt_number,
            "service_request": _sr_summary(sr) if sr else None,
        })
    return {"count": len(result), "offers": result}


@router.post("/offers/{offer_id}/accept")
def accept_offer(
    offer_id: str,
    current_user: User = Depends(get_current_technician),
    db: Session = Depends(get_db),
):
    p = _get_profile(db, current_user)
    offer = db.query(JobOffer).filter(
        JobOffer.id == offer_id,
        JobOffer.technician_profile_id == p.id,
    ).first()
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    if offer.status != OfferStatus.PENDING:
        raise HTTPException(status_code=409, detail=f"Offer is already '{offer.status.value}'")
    if datetime.utcnow() > offer.expires_at:
        raise HTTPException(status_code=410, detail="Offer has expired")
    try:
        result = handle_acceptance(db, offer_id)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return result


@router.post("/offers/{offer_id}/reject")
def reject_offer(
    offer_id: str,
    body: RejectOfferBody,
    current_user: User = Depends(get_current_technician),
    db: Session = Depends(get_db),
):
    p = _get_profile(db, current_user)
    offer = db.query(JobOffer).filter(
        JobOffer.id == offer_id,
        JobOffer.technician_profile_id == p.id,
    ).first()
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    if offer.status != OfferStatus.PENDING:
        raise HTTPException(status_code=409, detail=f"Offer is already '{offer.status.value}'")
    try:
        result = handle_rejection(db, offer_id, body.reason)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return result


# ── Jobs ──────────────────────────────────────────────────────────────────────

@router.get("/jobs")
def list_jobs(
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_technician),
    db: Session = Depends(get_db),
):
    p = _get_profile(db, current_user)
    q = db.query(ServiceRequest).filter(ServiceRequest.assigned_technician_id == p.id)
    if status_filter:
        q = q.filter(ServiceRequest.status == status_filter)
    total = q.count()
    items = q.order_by(ServiceRequest.created_at.desc()).offset(offset).limit(limit).all()
    return {"total": total, "limit": limit, "offset": offset, "jobs": [_sr_summary(sr) for sr in items]}


@router.get("/jobs/{job_id}")
def get_job(
    job_id: str,
    current_user: User = Depends(get_current_technician),
    db: Session = Depends(get_db),
):
    p = _get_profile(db, current_user)
    sr = db.query(ServiceRequest).filter(
        ServiceRequest.id == job_id,
        ServiceRequest.assigned_technician_id == p.id,
    ).first()
    if not sr:
        raise HTTPException(status_code=404, detail="Job not found")
    return _sr_summary(sr)


@router.patch("/jobs/{job_id}/status")
def update_job_status(
    job_id: str,
    body: JobStatusUpdate,
    current_user: User = Depends(get_current_technician),
    db: Session = Depends(get_db),
):
    p = _get_profile(db, current_user)
    sr = db.query(ServiceRequest).filter(
        ServiceRequest.id == job_id,
        ServiceRequest.assigned_technician_id == p.id,
    ).first()
    if not sr:
        raise HTTPException(status_code=404, detail="Job not found")

    current_str = sr.status.value
    allowed_next = VALID_STATUS_TRANSITIONS.get(current_str)
    if allowed_next != body.status:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot transition from '{current_str}' to '{body.status}'. Expected '{allowed_next}'.",
        )

    sr.status = RequestStatus(body.status)

    if body.status == "completed":
        now = datetime.utcnow()
        sr.completed_at = now

        # Mark SLA resolution
        if sr.sla_resolution_deadline:
            sr.sla_resolution_met = now <= sr.sla_resolution_deadline

        if not sr.estimated_price or sr.estimated_price <= 0:
            if sr.category and sr.created_at:
                duration = max(15.0, (now - sr.created_at).total_seconds() / 60.0)
                sr.estimated_price = round(duration * sr.category.price_per_minute, 2)
                sr.estimated_duration_minutes = int(duration)
            else:
                sr.estimated_price = 500.0

        p.total_jobs_completed = (p.total_jobs_completed or 0) + 1

        # Check or settle payment: if COD pending or no payment, create/mark as collected
        from app.models import Payment, PaymentMethod, PaymentStatus
        from app.services.payment_service import settle_revenue, generate_transaction_id

        existing_pay = db.query(Payment).filter(Payment.service_request_id == sr.id).first()
        if existing_pay:
            if existing_pay.payment_method == PaymentMethod.CASH and existing_pay.status == PaymentStatus.PENDING:
                existing_pay.status = PaymentStatus.COMPLETED
                existing_pay.paid_at = now
                existing_pay.transaction_id = generate_transaction_id(PaymentMethod.CASH)
            if not existing_pay.technician_profile_id:
                existing_pay.technician_profile_id = p.id
        else:
            amt = sr.estimated_price
            new_pay = Payment(
                service_request_id=sr.id,
                customer_id=sr.customer_id,
                technician_profile_id=p.id,
                amount=amt,
                admin_share=round(amt * 0.40, 2),
                technician_share=round(amt * 0.60, 2),
                payment_method=PaymentMethod.CASH,
                status=PaymentStatus.COMPLETED,
                transaction_id=generate_transaction_id(PaymentMethod.CASH),
                paid_at=now,
            )
            db.add(new_pay)

        db.commit()

        # Idempotently settle 60% revenue share to technician
        settle_revenue(db, sr)

        # Notify customer
        if sr.customer:
            notify(
                db, sr.customer.user_id, NotificationType.STATUS_CHANGED,
                "Job Completed",
                f"Your {sr.category.name if sr.category else 'service'} job has been completed. Please rate your technician!",
                entity_type="service_request", entity_id=sr.id,
            )

    db.commit()
    return {"message": f"Status updated to '{body.status}'", "job_id": job_id, "status": body.status}


@router.post("/jobs/{job_id}/notes")
def add_job_note(
    job_id: str,
    body: NoteBody,
    current_user: User = Depends(get_current_technician),
    db: Session = Depends(get_db),
):
    p = _get_profile(db, current_user)
    sr = db.query(ServiceRequest).filter(
        ServiceRequest.id == job_id,
        ServiceRequest.assigned_technician_id == p.id,
    ).first()
    if not sr:
        raise HTTPException(status_code=404, detail="Job not found")
    existing = sr.completion_notes or ""
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
    sr.completion_notes = f"{existing}\n[{timestamp}] {body.note}".strip()
    db.commit()
    return {"message": "Note added", "completion_notes": sr.completion_notes}


# ── Earnings & ratings ────────────────────────────────────────────────────────

@router.get("/earnings")
def get_earnings(
    current_user: User = Depends(get_current_technician),
    db: Session = Depends(get_db),
):
    p = _get_profile(db, current_user)
    from app.models import Payment, PaymentStatus
    completed_jobs = db.query(ServiceRequest).filter(
        ServiceRequest.assigned_technician_id == p.id,
        ServiceRequest.status == RequestStatus.COMPLETED,
    ).order_by(ServiceRequest.completed_at.desc()).all()

    payout_history = []
    total_tech_earnings = 0.0
    total_admin_commission = 0.0
    gross_volume = 0.0
    daily: dict[str, float] = {}

    for sr in completed_jobs:
        pay = db.query(Payment).filter(Payment.service_request_id == sr.id).order_by(Payment.created_at.desc()).first()
        amt = pay.amount if pay else (sr.estimated_price or 0.0)
        t_share = pay.technician_share if pay else round(amt * 0.60, 2)
        a_share = pay.admin_share if pay else round(amt * 0.40, 2)
        p_status = pay.status.value if pay else "completed"
        p_method = pay.payment_method.value if pay else "cash"
        tx_id = pay.transaction_id if pay else f"SETTLED-{sr.id[:8].upper()}"

        if p_status == "completed":
            total_tech_earnings += t_share
            total_admin_commission += a_share
            gross_volume += amt

            if sr.completed_at:
                day = sr.completed_at.strftime("%Y-%m-%d")
                daily[day] = round(daily.get(day, 0.0) + t_share, 2)

        payout_history.append({
            "booking_id": sr.id,
            "service_name": sr.category.name if sr.category else "Service",
            "customer_name": sr.customer.name if sr.customer else "Customer",
            "completed_at": sr.completed_at.isoformat() if sr.completed_at else None,
            "booking_amount": amt,
            "technician_share": t_share,
            "admin_share": a_share,
            "payment_method": p_method,
            "payment_status": p_status,
            "transaction_id": tx_id,
        })

    p.total_earnings = round(total_tech_earnings, 2)
    db.commit()

    return {
        "total_earnings": p.total_earnings,
        "admin_commission_deducted": round(total_admin_commission, 2),
        "gross_revenue": round(gross_volume, 2),
        "total_jobs_completed": len(completed_jobs),
        "daily_breakdown": [{"date": k, "earnings": v} for k, v in sorted(daily.items(), reverse=True)],
        "payout_history": payout_history,
    }


@router.get("/ratings")
def get_ratings(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_technician),
    db: Session = Depends(get_db),
):
    p = _get_profile(db, current_user)
    q = db.query(Rating).filter(Rating.technician_profile_id == p.id)
    total = q.count()
    items = q.order_by(Rating.created_at.desc()).offset(offset).limit(limit).all()
    return {
        "avg_rating": p.avg_rating,
        "total": total,
        "ratings": [
            {
                "id": r.id,
                "score": r.score,
                "feedback_text": r.feedback_text,
                "service_request_id": r.service_request_id,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in items
        ],
    }


# ── Notifications ─────────────────────────────────────────────────────────────

@router.get("/notifications")
def get_notifications(
    unread_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_technician),
    db: Session = Depends(get_db),
):
    q = db.query(Notification).filter(Notification.user_id == current_user.id)
    if unread_only:
        q = q.filter(Notification.is_read == False)  # noqa: E712
    total = q.count()
    items = q.order_by(Notification.created_at.desc()).offset(offset).limit(limit).all()
    return {
        "total": total,
        "notifications": [
            {
                "id": n.id,
                "type": n.type.value,
                "title": n.title,
                "body": n.body,
                "is_read": n.is_read,
                "entity_type": n.entity_type,
                "entity_id": n.entity_id,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in items
        ],
    }


@router.patch("/notifications/{notification_id}/read")
def mark_notification_read(
    notification_id: str,
    current_user: User = Depends(get_current_technician),
    db: Session = Depends(get_db),
):
    try:
        mark_read(db, notification_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"message": "Marked as read"}

