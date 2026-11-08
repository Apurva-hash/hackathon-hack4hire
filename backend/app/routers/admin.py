"""Admin API router — dashboard, CRUD, config, audit, export.

All endpoints require a valid JWT with role=admin.
Prefix: /api/admin
"""

from __future__ import annotations

import csv
import io
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_admin
from app.models import (
    User, Customer, TechnicianProfile, ServiceCategory, ServiceRequest,
    JobOffer, Rating, AuditLog, Notification, SLATier, SLAEvent, MatchingConfig,
    RequestStatus, RequestUrgency, OfferStatus, NotificationType, UserRole,
)
from app.models.base import generate_uuid
from app.services.sla_service import get_sla_stats
from app.services.matching_service import dispatch

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Admin"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _audit(
    db: Session,
    admin_user_id: str,
    action: str,
    entity_type: str,
    entity_id: Optional[str] = None,
    old_value=None,
    new_value=None,
):
    """Write an immutable AuditLog entry."""
    log = AuditLog(
        id=generate_uuid(),
        admin_user_id=admin_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        old_value=old_value,
        new_value=new_value,
        occurred_at=datetime.utcnow(),
    )
    db.add(log)


def _parse_date(date_str: Optional[str], label: str) -> Optional[datetime]:
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid {label} format (use ISO 8601)")


# ── Dashboard: overview ───────────────────────────────────────────────────────

@router.get("/dashboard/overview")
def dashboard_overview(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    df = _parse_date(date_from, "date_from")
    dt = _parse_date(date_to, "date_to")

    total_customers = db.query(func.count(Customer.id)).scalar()
    total_techs = db.query(func.count(TechnicianProfile.id)).scalar()
    online_techs = db.query(func.count(TechnicianProfile.id)).filter(TechnicianProfile.is_online == True).scalar()  # noqa: E712
    approved_techs = db.query(func.count(TechnicianProfile.id)).filter(TechnicianProfile.is_approved == True).scalar()  # noqa: E712
    suspended_techs = db.query(func.count(TechnicianProfile.id)).filter(TechnicianProfile.is_suspended == True).scalar()  # noqa: E712

    sr_q = db.query(ServiceRequest)
    if df:
        sr_q = sr_q.filter(ServiceRequest.created_at >= df)
    if dt:
        sr_q = sr_q.filter(ServiceRequest.created_at <= dt)

    total_jobs = sr_q.count()

    status_counts = {}
    for s in RequestStatus:
        status_counts[s.value] = sr_q.filter(ServiceRequest.status == s).count()

    # Oldest unassigned
    oldest_pending = (
        sr_q.filter(ServiceRequest.status == RequestStatus.REQUESTED)
        .order_by(ServiceRequest.created_at.asc())
        .first()
    )

    escalated_count = sr_q.filter(ServiceRequest.escalated_to_admin == True).count()  # noqa: E712

    return {
        "customers": {"total": total_customers},
        "technicians": {
            "total": total_techs,
            "online": online_techs,
            "offline": total_techs - online_techs,
            "approved": approved_techs,
            "suspended": suspended_techs,
        },
        "jobs": {
            "total": total_jobs,
            "by_status": status_counts,
            "escalated": escalated_count,
        },
        "oldest_pending": {
            "id": oldest_pending.id,
            "created_at": oldest_pending.created_at.isoformat() if oldest_pending and oldest_pending.created_at else None,
            "age_hours": round((datetime.utcnow() - oldest_pending.created_at).total_seconds() / 3600, 1) if oldest_pending and oldest_pending.created_at else None,
        } if oldest_pending else None,
    }


# ── Dashboard: dispatch metrics ───────────────────────────────────────────────

@router.get("/dashboard/dispatch")
def dashboard_dispatch(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    df = _parse_date(date_from, "date_from")
    dt = _parse_date(date_to, "date_to")

    offer_q = db.query(JobOffer)
    if df or dt:
        offer_q = offer_q.join(ServiceRequest, JobOffer.service_request_id == ServiceRequest.id)
        if df:
            offer_q = offer_q.filter(ServiceRequest.created_at >= df)
        if dt:
            offer_q = offer_q.filter(ServiceRequest.created_at <= dt)

    total_offers = offer_q.count()
    accepted = offer_q.filter(JobOffer.status == OfferStatus.ACCEPTED).count()
    rejected = offer_q.filter(JobOffer.status == OfferStatus.REJECTED).count()
    expired = offer_q.filter(JobOffer.status == OfferStatus.EXPIRED).count()

    # Reassignment count: jobs that received more than 1 offer attempt
    sr_q = db.query(ServiceRequest)
    if df:
        sr_q = sr_q.filter(ServiceRequest.created_at >= df)
    if dt:
        sr_q = sr_q.filter(ServiceRequest.created_at <= dt)
    reassigned = sr_q.filter(ServiceRequest.offer_attempt > 1).count()
    assigned = sr_q.filter(ServiceRequest.offer_attempt >= 1).count()
    total_sr = sr_q.count()

    assignment_rate = round(assigned / total_sr * 100, 2) if total_sr else 0.0
    acceptance_rate = round(accepted / total_offers * 100, 2) if total_offers else 0.0
    rejection_rate = round(rejected / total_offers * 100, 2) if total_offers else 0.0

    # Average time to assign (created_at → first accepted offer)
    accepted_offers = offer_q.filter(JobOffer.status == OfferStatus.ACCEPTED).all()
    time_to_assign_list = []
    for o in accepted_offers:
        sr = o.service_request
        if sr and sr.created_at and o.offered_at:
            delta = (o.offered_at - sr.created_at).total_seconds() / 60
            time_to_assign_list.append(delta)
    avg_time_to_assign = round(sum(time_to_assign_list) / len(time_to_assign_list), 2) if time_to_assign_list else None

    return {
        "total_offers": total_offers,
        "accepted": accepted,
        "rejected": rejected,
        "expired": expired,
        "reassignment_count": reassigned,
        "assignment_rate_pct": assignment_rate,
        "acceptance_rate_pct": acceptance_rate,
        "rejection_rate_pct": rejection_rate,
        "avg_time_to_assign_minutes": avg_time_to_assign,
    }


# ── Dashboard: workload ───────────────────────────────────────────────────────

@router.get("/dashboard/workload")
def dashboard_workload(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    techs = db.query(TechnicianProfile).all()
    terminal = {RequestStatus.COMPLETED.value, RequestStatus.CANCELLED.value, RequestStatus.ESCALATED.value}
    result = []
    for t in techs:
        active = (
            db.query(func.count(ServiceRequest.id))
            .filter(
                ServiceRequest.assigned_technician_id == t.id,
                ServiceRequest.status.notin_(list(terminal)),
            )
            .scalar() or 0
        )
        utilization = round(active / t.max_concurrent_jobs * 100, 1) if t.max_concurrent_jobs else 0.0
        result.append({
            "technician_id": t.id,
            "name": t.name,
            "is_online": t.is_online,
            "active_jobs": active,
            "max_concurrent_jobs": t.max_concurrent_jobs,
            "utilization_pct": utilization,
            "capacity_left": max(0, t.max_concurrent_jobs - active),
            "total_completed": t.total_jobs_completed,
            "avg_rating": t.avg_rating,
        })
    result.sort(key=lambda x: x["utilization_pct"], reverse=True)
    return {"technicians": result}


# ── Dashboard: SLA ────────────────────────────────────────────────────────────

@router.get("/dashboard/sla")
def dashboard_sla(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    df = _parse_date(date_from, "date_from")
    dt = _parse_date(date_to, "date_to")
    return get_sla_stats(db, date_from=df, date_to=dt)


# ── Dashboard: feedback ───────────────────────────────────────────────────────

@router.get("/dashboard/feedback")
def dashboard_feedback(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    df = _parse_date(date_from, "date_from")
    dt = _parse_date(date_to, "date_to")

    q = db.query(Rating)
    if df:
        q = q.filter(Rating.created_at >= df)
    if dt:
        q = q.filter(Rating.created_at <= dt)

    total = q.count()
    avg = db.query(func.avg(Rating.score)).scalar()

    distribution = {}
    for score_int in range(1, 6):
        distribution[str(score_int)] = q.filter(
            Rating.score >= score_int, Rating.score < score_int + 1
        ).count()

    low_rating_count = q.filter(Rating.score < 3.0).count()

    recent = q.order_by(Rating.created_at.desc()).limit(limit).all()

    return {
        "total_reviews": total,
        "avg_rating": round(avg, 2) if avg else None,
        "distribution": distribution,
        "low_rating_count": low_rating_count,
        "recent_reviews": [
            {
                "id": r.id,
                "score": r.score,
                "feedback_text": r.feedback_text,
                "technician_id": r.technician_profile_id,
                "service_request_id": r.service_request_id,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in recent
        ],
    }


# ── Dashboard: revenue ────────────────────────────────────────────────────────

@router.get("/dashboard/revenue")
def dashboard_revenue(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    df = _parse_date(date_from, "date_from")
    dt = _parse_date(date_to, "date_to")

    from app.models import Payment, PaymentStatus
    completed_payments = db.query(Payment).filter(Payment.status == PaymentStatus.COMPLETED).all()

    total_revenue_from_payments = sum(p.amount for p in completed_payments)
    total_rev_sr = db.query(func.sum(ServiceRequest.estimated_price)).filter(
        ServiceRequest.status == RequestStatus.COMPLETED
    ).scalar() or 0.0

    effective_revenue = round(max(total_revenue_from_payments, total_rev_sr), 2)
    admin_earnings = round(effective_revenue * 0.40, 2)
    technician_payouts = round(effective_revenue * 0.60, 2)

    # Top earning technicians
    techs = (
        db.query(TechnicianProfile)
        .filter(TechnicianProfile.total_earnings > 0)
        .order_by(TechnicianProfile.total_earnings.desc())
        .limit(10)
        .all()
    )

    # Method breakdown
    method_counts = {}
    for p in completed_payments:
        m = p.payment_method.value
        method_counts[m] = method_counts.get(m, 0) + 1

    return {
        "total_revenue": effective_revenue,
        "admin_earnings": admin_earnings,
        "technician_payouts": technician_payouts,
        "admin_share_percentage": 40,
        "technician_share_percentage": 60,
        "total_completed_jobs": db.query(ServiceRequest).filter(ServiceRequest.status == RequestStatus.COMPLETED).count(),
        "payment_method_breakdown": method_counts,
        "top_earning_technicians": [
            {
                "id": t.id,
                "name": t.name,
                "total_earnings": t.total_earnings,
                "total_jobs_completed": t.total_jobs_completed,
                "avg_rating": t.avg_rating,
            }
            for t in techs
        ],
    }


@router.get("/payments")
def list_payments(
    status: Optional[str] = Query(None),
    payment_method: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    from app.models import Payment, PaymentStatus
    q = db.query(Payment)
    if status:
        q = q.filter(Payment.status == status)
    if payment_method:
        q = q.filter(Payment.payment_method == payment_method)

    total = q.count()
    items = q.order_by(Payment.created_at.desc()).offset(offset).limit(limit).all()

    completed_payments = db.query(Payment).filter(Payment.status == PaymentStatus.COMPLETED).all()
    total_rev = round(sum(p.amount for p in completed_payments), 2)
    admin_share = round(total_rev * 0.40, 2)
    technician_payouts = round(total_rev * 0.60, 2)

    return {
        "total": total,
        "total_revenue": total_rev,
        "admin_earnings": admin_share,
        "technician_payouts": technician_payouts,
        "payments": [
            {
                "id": p.id,
                "transaction_id": p.transaction_id,
                "service_request_id": p.service_request_id,
                "service_category": p.service_request.category.name if p.service_request and p.service_request.category else "Home Service",
                "customer_name": p.customer.name if p.customer else "Customer",
                "technician_name": p.technician_profile.name if p.technician_profile else "Unassigned",
                "amount": p.amount,
                "admin_share": p.admin_share,
                "technician_share": p.technician_share,
                "payment_method": p.payment_method.value,
                "status": p.status.value,
                "failure_reason": p.failure_reason,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "paid_at": p.paid_at.isoformat() if p.paid_at else None,
            }
            for p in items
        ],
    }


# ── Dashboard: demand ─────────────────────────────────────────────────────────

@router.get("/dashboard/demand")
def dashboard_demand(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    df = _parse_date(date_from, "date_from")
    dt = _parse_date(date_to, "date_to")

    q = db.query(ServiceRequest)
    if df:
        q = q.filter(ServiceRequest.created_at >= df)
    if dt:
        q = q.filter(ServiceRequest.created_at <= dt)

    all_requests = q.all()

    # By hour of day
    by_hour: dict[int, int] = {h: 0 for h in range(24)}
    by_category: dict[str, int] = {}
    by_urgency: dict[str, int] = {}

    for sr in all_requests:
        if sr.created_at:
            by_hour[sr.created_at.hour] = by_hour.get(sr.created_at.hour, 0) + 1
        cat_name = sr.category.name if sr.category else "Unknown"
        by_category[cat_name] = by_category.get(cat_name, 0) + 1
        urg = sr.urgency.value if sr.urgency else "normal"
        by_urgency[urg] = by_urgency.get(urg, 0) + 1

    return {
        "by_hour": [{"hour": h, "count": by_hour[h]} for h in range(24)],
        "by_category": [{"category": k, "count": v} for k, v in sorted(by_category.items(), key=lambda x: -x[1])],
        "by_urgency": by_urgency,
    }


# ── Customers ─────────────────────────────────────────────────────────────────

@router.get("/customers")
def list_customers(
    search: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    q = db.query(Customer).join(User, Customer.user_id == User.id)
    if search:
        q = q.filter(Customer.name.ilike(f"%{search}%"))
    if is_active is not None:
        q = q.filter(User.is_active == is_active)
    total = q.count()
    items = q.offset(offset).limit(limit).all()
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "customers": [
            {
                "id": c.id,
                "user_id": c.user_id,
                "name": c.name,
                "phone": c.phone,
                "avg_rating": c.avg_rating,
                "total_bookings": c.total_bookings,
                "is_active": c.user.is_active if c.user else None,
            }
            for c in items
        ],
    }


@router.get("/customers/{customer_id}")
def get_customer(
    customer_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    c = db.query(Customer).filter(Customer.id == customer_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Customer not found")
    bookings = db.query(ServiceRequest).filter(ServiceRequest.customer_id == c.id).all()
    return {
        "id": c.id,
        "user_id": c.user_id,
        "name": c.name,
        "phone": c.phone,
        "avg_rating": c.avg_rating,
        "total_bookings": c.total_bookings,
        "saved_addresses": c.saved_addresses,
        "is_active": c.user.is_active if c.user else None,
        "booking_history": [
            {"id": sr.id, "status": sr.status.value, "created_at": sr.created_at.isoformat() if sr.created_at else None}
            for sr in bookings
        ],
    }


class CustomerUpdate(BaseModel):
    is_active: Optional[bool] = None
    name: Optional[str] = None


@router.patch("/customers/{customer_id}")
def update_customer(
    customer_id: str,
    body: CustomerUpdate,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    c = db.query(Customer).filter(Customer.id == customer_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Customer not found")
    old = {"name": c.name, "is_active": c.user.is_active if c.user else None}
    if body.name is not None:
        c.name = body.name
    if body.is_active is not None and c.user:
        c.user.is_active = body.is_active
    db.commit()
    _audit(db, current_user.id, "update_customer", "customer", customer_id, old, body.dict(exclude_none=True))
    db.commit()
    return {"message": "Customer updated"}


# ── Technicians ───────────────────────────────────────────────────────────────

@router.get("/technicians")
def list_technicians(
    search: Optional[str] = Query(None),
    is_online: Optional[bool] = Query(None),
    is_approved: Optional[bool] = Query(None),
    is_suspended: Optional[bool] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    q = db.query(TechnicianProfile)
    if search:
        q = q.filter(TechnicianProfile.name.ilike(f"%{search}%"))
    if is_online is not None:
        q = q.filter(TechnicianProfile.is_online == is_online)
    if is_approved is not None:
        q = q.filter(TechnicianProfile.is_approved == is_approved)
    if is_suspended is not None:
        q = q.filter(TechnicianProfile.is_suspended == is_suspended)
    total = q.count()
    items = q.offset(offset).limit(limit).all()
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "technicians": [
            {
                "id": t.id,
                "name": t.name,
                "phone": t.phone,
                "is_online": t.is_online,
                "is_approved": t.is_approved,
                "is_suspended": t.is_suspended,
                "lat": t.lat,
                "lng": t.lng,
                "certification_level": t.certification_level,
                "avg_rating": t.avg_rating,
                "total_jobs_completed": t.total_jobs_completed,
                "acceptance_rate": t.acceptance_rate,
                "total_earnings": t.total_earnings,
                "service_radius_km": t.service_radius_km,
            }
            for t in items
        ],
    }


@router.get("/technicians/{tech_id}")
def get_technician(
    tech_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    t = db.query(TechnicianProfile).filter(TechnicianProfile.id == tech_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Technician not found")
    return {
        "id": t.id,
        "user_id": t.user_id,
        "name": t.name,
        "phone": t.phone,
        "bio": t.bio,
        "is_online": t.is_online,
        "is_approved": t.is_approved,
        "is_suspended": t.is_suspended,
        "lat": t.lat,
        "lng": t.lng,
        "service_radius_km": t.service_radius_km,
        "max_concurrent_jobs": t.max_concurrent_jobs,
        "certification_level": t.certification_level,
        "avg_rating": t.avg_rating,
        "total_jobs_completed": t.total_jobs_completed,
        "total_jobs_rejected": t.total_jobs_rejected,
        "acceptance_rate": t.acceptance_rate,
        "total_earnings": t.total_earnings,
    }


class TechUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    certification_level: Optional[int] = None
    service_radius_km: Optional[float] = None
    max_concurrent_jobs: Optional[int] = None


@router.patch("/technicians/{tech_id}")
def update_technician(
    tech_id: str,
    body: TechUpdate,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    t = db.query(TechnicianProfile).filter(TechnicianProfile.id == tech_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Technician not found")
    old = {"name": t.name, "certification_level": t.certification_level}
    if body.name is not None:
        t.name = body.name
    if body.phone is not None:
        t.phone = body.phone
    if body.certification_level is not None:
        t.certification_level = max(1, min(5, body.certification_level))
    if body.service_radius_km is not None:
        t.service_radius_km = body.service_radius_km
    if body.max_concurrent_jobs is not None:
        t.max_concurrent_jobs = max(1, body.max_concurrent_jobs)
    db.commit()
    _audit(db, current_user.id, "update_technician", "technician_profile", tech_id, old, body.dict(exclude_none=True))
    db.commit()
    return {"message": "Technician updated"}


@router.patch("/technicians/{tech_id}/approve")
def approve_technician(
    tech_id: str,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    t = db.query(TechnicianProfile).filter(TechnicianProfile.id == tech_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Technician not found")
    t.is_approved = True
    t.is_suspended = False
    db.commit()
    _audit(db, current_user.id, "approve_technician", "technician_profile", tech_id)
    db.commit()
    # Notify technician
    from app.services.notification_service import notify
    notify(db, t.user_id, NotificationType.ADMIN_ACTION, "Account Approved",
           "Your account has been approved. You can now go online and accept jobs.", "technician_profile", t.id)
    db.commit()
    return {"message": "Technician approved"}


@router.patch("/technicians/{tech_id}/suspend")
def suspend_technician(
    tech_id: str,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    t = db.query(TechnicianProfile).filter(TechnicianProfile.id == tech_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Technician not found")
    t.is_suspended = True
    t.is_online = False
    db.commit()
    _audit(db, current_user.id, "suspend_technician", "technician_profile", tech_id)
    db.commit()
    from app.services.notification_service import notify
    notify(db, t.user_id, NotificationType.ADMIN_ACTION, "Account Suspended",
           "Your account has been suspended. Please contact support.", "technician_profile", t.id)
    db.commit()
    return {"message": "Technician suspended"}


# ── Jobs ──────────────────────────────────────────────────────────────────────

@router.get("/jobs")
def list_jobs(
    status: Optional[str] = Query(None),
    urgency: Optional[str] = Query(None),
    category_id: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    df = _parse_date(date_from, "date_from")
    dt = _parse_date(date_to, "date_to")

    q = db.query(ServiceRequest)
    if status:
        q = q.filter(ServiceRequest.status == status)
    if urgency:
        q = q.filter(ServiceRequest.urgency == urgency)
    if category_id:
        q = q.filter(ServiceRequest.category_id == category_id)
    if df:
        q = q.filter(ServiceRequest.created_at >= df)
    if dt:
        q = q.filter(ServiceRequest.created_at <= dt)

    total = q.count()
    items = q.order_by(ServiceRequest.created_at.desc()).offset(offset).limit(limit).all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "jobs": [
            {
                "id": sr.id,
                "status": sr.status.value if sr.status else None,
                "urgency": sr.urgency.value if sr.urgency else None,
                "category": sr.category.name if sr.category else None,
                "description": sr.description,
                "address": sr.address,
                "customer_id": sr.customer_id,
                "assigned_technician_id": sr.assigned_technician_id,
                "offer_attempt": sr.offer_attempt,
                "escalated": sr.escalated_to_admin,
                "estimated_price": sr.estimated_price,
                "created_at": sr.created_at.isoformat() if sr.created_at else None,
                "completed_at": sr.completed_at.isoformat() if sr.completed_at else None,
            }
            for sr in items
        ],
    }


@router.get("/jobs/{job_id}")
def get_job(
    job_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    sr = db.query(ServiceRequest).filter(ServiceRequest.id == job_id).first()
    if not sr:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "id": sr.id,
        "status": sr.status.value if sr.status else None,
        "urgency": sr.urgency.value if sr.urgency else None,
        "category_id": sr.category_id,
        "category": sr.category.name if sr.category else None,
        "description": sr.description,
        "address": sr.address,
        "lat": sr.lat,
        "lng": sr.lng,
        "customer_id": sr.customer_id,
        "assigned_technician_id": sr.assigned_technician_id,
        "offer_attempt": sr.offer_attempt,
        "escalated": sr.escalated_to_admin,
        "sla_response_deadline": sr.sla_response_deadline.isoformat() if sr.sla_response_deadline else None,
        "sla_resolution_deadline": sr.sla_resolution_deadline.isoformat() if sr.sla_resolution_deadline else None,
        "sla_response_met": sr.sla_response_met,
        "sla_resolution_met": sr.sla_resolution_met,
        "estimated_price": sr.estimated_price,
        "completion_notes": sr.completion_notes,
        "created_at": sr.created_at.isoformat() if sr.created_at else None,
        "completed_at": sr.completed_at.isoformat() if sr.completed_at else None,
        "offers": [
            {
                "id": o.id,
                "technician_id": o.technician_profile_id,
                "status": o.status.value,
                "attempt_number": o.attempt_number,
                "offered_at": o.offered_at.isoformat() if o.offered_at else None,
                "rejection_reason": o.rejection_reason,
            }
            for o in sr.offers
        ],
    }


class AssignBody(BaseModel):
    technician_profile_id: str


@router.patch("/jobs/{job_id}/assign")
def manual_assign(
    job_id: str,
    body: AssignBody,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    sr = db.query(ServiceRequest).filter(ServiceRequest.id == job_id).first()
    if not sr:
        raise HTTPException(status_code=404, detail="Job not found")
    tech = db.query(TechnicianProfile).filter(TechnicianProfile.id == body.technician_profile_id).first()
    if not tech:
        raise HTTPException(status_code=404, detail="Technician not found")

    old_tech = sr.assigned_technician_id
    sr.assigned_technician_id = body.technician_profile_id
    sr.status = RequestStatus.ASSIGNED
    sr.escalated_to_admin = False
    db.commit()
    _audit(db, current_user.id, "manual_assign", "service_request", job_id,
           {"technician": old_tech}, {"technician": body.technician_profile_id})
    db.commit()
    return {"message": "Job manually assigned", "technician_id": body.technician_profile_id}


@router.patch("/jobs/{job_id}/reassign")
def reassign_job(
    job_id: str,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Trigger automatic re-dispatch for an escalated or stuck job."""
    sr = db.query(ServiceRequest).filter(ServiceRequest.id == job_id).first()
    if not sr:
        raise HTTPException(status_code=404, detail="Job not found")

    sr.escalated_to_admin = False
    db.commit()
    try:
        result = dispatch(db, job_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    _audit(db, current_user.id, "reassign_job", "service_request", job_id)
    db.commit()
    return result


@router.patch("/jobs/{job_id}/cancel")
def cancel_job(
    job_id: str,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    sr = db.query(ServiceRequest).filter(ServiceRequest.id == job_id).first()
    if not sr:
        raise HTTPException(status_code=404, detail="Job not found")
    if sr.status in {RequestStatus.COMPLETED, RequestStatus.CANCELLED}:
        raise HTTPException(status_code=409, detail="Job already completed or cancelled")
    sr.status = RequestStatus.CANCELLED
    for o in sr.offers:
        if o.status == OfferStatus.PENDING:
            o.status = OfferStatus.EXPIRED
    db.commit()
    _audit(db, current_user.id, "cancel_job", "service_request", job_id)
    db.commit()
    return {"message": "Job cancelled"}


# ── Config: SLA tiers ─────────────────────────────────────────────────────────

@router.get("/config/sla-tiers")
def list_sla_tiers(db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    tiers = db.query(SLATier).order_by(SLATier.priority_level.asc()).all()
    return [
        {
            "id": t.id,
            "name": t.name,
            "priority_level": t.priority_level,
            "response_time_minutes": t.response_time_minutes,
            "resolution_time_minutes": t.resolution_time_minutes,
            "is_default": t.is_default,
        }
        for t in tiers
    ]


class SLATierCreate(BaseModel):
    name: str
    priority_level: int = Field(..., ge=1, le=4)
    response_time_minutes: int = Field(..., gt=0)
    resolution_time_minutes: int = Field(..., gt=0)
    is_default: bool = False


@router.post("/config/sla-tiers", status_code=201)
def create_sla_tier(
    body: SLATierCreate,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    if body.is_default:
        # Clear existing default
        db.query(SLATier).filter(SLATier.is_default == True).update({"is_default": False})  # noqa: E712
    tier = SLATier(
        id=generate_uuid(),
        name=body.name,
        priority_level=body.priority_level,
        response_time_minutes=body.response_time_minutes,
        resolution_time_minutes=body.resolution_time_minutes,
        is_default=body.is_default,
    )
    db.add(tier)
    db.commit()
    _audit(db, current_user.id, "create_sla_tier", "sla_tier", tier.id, None, body.dict())
    db.commit()
    return {"id": tier.id, "message": "SLA tier created"}


class SLATierUpdate(BaseModel):
    name: Optional[str] = None
    priority_level: Optional[int] = None
    response_time_minutes: Optional[int] = None
    resolution_time_minutes: Optional[int] = None
    is_default: Optional[bool] = None


@router.patch("/config/sla-tiers/{tier_id}")
def update_sla_tier(
    tier_id: str,
    body: SLATierUpdate,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    tier = db.query(SLATier).filter(SLATier.id == tier_id).first()
    if not tier:
        raise HTTPException(status_code=404, detail="SLA tier not found")
    old = {"name": tier.name, "priority_level": tier.priority_level}
    if body.name is not None:
        tier.name = body.name
    if body.priority_level is not None:
        tier.priority_level = body.priority_level
    if body.response_time_minutes is not None:
        tier.response_time_minutes = body.response_time_minutes
    if body.resolution_time_minutes is not None:
        tier.resolution_time_minutes = body.resolution_time_minutes
    if body.is_default is not None:
        if body.is_default:
            db.query(SLATier).filter(SLATier.is_default == True).update({"is_default": False})  # noqa: E712
        tier.is_default = body.is_default
    db.commit()
    _audit(db, current_user.id, "update_sla_tier", "sla_tier", tier_id, old, body.dict(exclude_none=True))
    db.commit()
    return {"message": "SLA tier updated"}


@router.delete("/config/sla-tiers/{tier_id}", status_code=200)
def delete_sla_tier(
    tier_id: str,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    tier = db.query(SLATier).filter(SLATier.id == tier_id).first()
    if not tier:
        raise HTTPException(status_code=404, detail="SLA tier not found")
    db.delete(tier)
    db.commit()
    _audit(db, current_user.id, "delete_sla_tier", "sla_tier", tier_id)
    db.commit()
    return {"message": "SLA tier deleted"}


# ── Config: matching weights ──────────────────────────────────────────────────

@router.get("/config/matching")
def get_matching_config(db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    cfg = db.query(MatchingConfig).first()
    if not cfg:
        raise HTTPException(status_code=404, detail="Matching config not found")
    return {
        "weight_distance": cfg.weight_distance,
        "weight_rating": cfg.weight_rating,
        "weight_workload": cfg.weight_workload,
        "weight_skill_level": cfg.weight_skill_level,
        "weight_acceptance_rate": cfg.weight_acceptance_rate,
        "offer_timeout_seconds": cfg.offer_timeout_seconds,
        "max_offer_attempts": cfg.max_offer_attempts,
        "high_risk_min_certification": cfg.high_risk_min_certification,
        "high_risk_wider_radius_km": cfg.high_risk_wider_radius_km,
        "high_risk_offer_timeout_seconds": cfg.high_risk_offer_timeout_seconds,
    }


class MatchingConfigUpdate(BaseModel):
    weight_distance: Optional[float] = None
    weight_rating: Optional[float] = None
    weight_workload: Optional[float] = None
    weight_skill_level: Optional[float] = None
    weight_acceptance_rate: Optional[float] = None
    offer_timeout_seconds: Optional[int] = None
    max_offer_attempts: Optional[int] = None
    high_risk_min_certification: Optional[int] = None
    high_risk_wider_radius_km: Optional[float] = None
    high_risk_offer_timeout_seconds: Optional[int] = None


@router.patch("/config/matching")
def update_matching_config(
    body: MatchingConfigUpdate,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    cfg = db.query(MatchingConfig).first()
    if not cfg:
        raise HTTPException(status_code=404, detail="Matching config not found")
    old = {k: getattr(cfg, k) for k in body.__fields__ if hasattr(cfg, k)}
    for field, val in body.dict(exclude_none=True).items():
        setattr(cfg, field, val)
    db.commit()
    _audit(db, current_user.id, "update_matching_config", "matching_config", "1", old, body.dict(exclude_none=True))
    db.commit()
    return {"message": "Matching config updated"}


# ── Config: service categories ────────────────────────────────────────────────

@router.get("/config/categories")
def list_categories(db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    cats = db.query(ServiceCategory).all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "description": c.description,
            "icon": c.icon,
            "price_per_minute": c.price_per_minute,
            "required_certification_level": c.required_certification_level,
            "is_active": c.is_active,
            "skill_id": c.skill_id,
        }
        for c in cats
    ]


class CategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None
    price_per_minute: float = Field(2.0, gt=0)
    required_certification_level: int = Field(1, ge=1, le=5)
    skill_id: Optional[str] = None
    is_active: bool = True


@router.post("/config/categories", status_code=201)
def create_category(
    body: CategoryCreate,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    cat = ServiceCategory(
        id=generate_uuid(),
        name=body.name,
        description=body.description,
        icon=body.icon,
        price_per_minute=body.price_per_minute,
        required_certification_level=body.required_certification_level,
        skill_id=body.skill_id,
        is_active=body.is_active,
    )
    db.add(cat)
    db.commit()
    _audit(db, current_user.id, "create_category", "service_category", cat.id, None, body.dict())
    db.commit()
    return {"id": cat.id, "message": "Category created"}


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    price_per_minute: Optional[float] = None
    required_certification_level: Optional[int] = None
    skill_id: Optional[str] = None
    is_active: Optional[bool] = None


@router.patch("/config/categories/{cat_id}")
def update_category(
    cat_id: str,
    body: CategoryUpdate,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    cat = db.query(ServiceCategory).filter(ServiceCategory.id == cat_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    old = {"name": cat.name, "is_active": cat.is_active}
    for field, val in body.dict(exclude_none=True).items():
        setattr(cat, field, val)
    db.commit()
    _audit(db, current_user.id, "update_category", "service_category", cat_id, old, body.dict(exclude_none=True))
    db.commit()
    return {"message": "Category updated"}


@router.delete("/config/categories/{cat_id}")
def delete_category(
    cat_id: str,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    cat = db.query(ServiceCategory).filter(ServiceCategory.id == cat_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    cat.is_active = False  # Soft-delete
    db.commit()
    _audit(db, current_user.id, "deactivate_category", "service_category", cat_id)
    db.commit()
    return {"message": "Category deactivated"}


# ── Audit log ─────────────────────────────────────────────────────────────────

@router.get("/audit-log")
def get_audit_log(
    entity_type: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    q = db.query(AuditLog)
    if entity_type:
        q = q.filter(AuditLog.entity_type == entity_type)
    if action:
        q = q.filter(AuditLog.action == action)
    total = q.count()
    items = q.order_by(AuditLog.occurred_at.desc()).offset(offset).limit(limit).all()
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "entries": [
            {
                "id": a.id,
                "admin_user_id": a.admin_user_id,
                "action": a.action,
                "entity_type": a.entity_type,
                "entity_id": a.entity_id,
                "old_value": a.old_value,
                "new_value": a.new_value,
                "occurred_at": a.occurred_at.isoformat() if a.occurred_at else None,
            }
            for a in items
        ],
    }


# ── CSV Exports ───────────────────────────────────────────────────────────────

@router.get("/export/jobs")
def export_jobs_csv(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    jobs = db.query(ServiceRequest).all()

    def generate():
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow([
            "id", "status", "urgency", "category", "description",
            "address", "customer_id", "assigned_technician_id",
            "offer_attempt", "escalated", "estimated_price",
            "created_at", "completed_at",
        ])
        yield buf.getvalue()
        buf.seek(0); buf.truncate(0)
        for sr in jobs:
            writer.writerow([
                sr.id, sr.status.value if sr.status else "", sr.urgency.value if sr.urgency else "",
                sr.category.name if sr.category else "", sr.description or "",
                sr.address, sr.customer_id, sr.assigned_technician_id or "",
                sr.offer_attempt, sr.escalated_to_admin,
                sr.estimated_price or "",
                sr.created_at.isoformat() if sr.created_at else "",
                sr.completed_at.isoformat() if sr.completed_at else "",
            ])
            yield buf.getvalue()
            buf.seek(0); buf.truncate(0)

    return StreamingResponse(
        generate(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=jobs.csv"},
    )


@router.get("/export/technicians")
def export_technicians_csv(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    techs = db.query(TechnicianProfile).all()

    def generate():
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow([
            "id", "name", "phone", "is_online", "is_approved", "is_suspended",
            "certification_level", "avg_rating", "total_jobs_completed",
            "total_jobs_rejected", "acceptance_rate", "total_earnings",
            "service_radius_km",
        ])
        yield buf.getvalue()
        buf.seek(0); buf.truncate(0)
        for t in techs:
            writer.writerow([
                t.id, t.name, t.phone or "", t.is_online, t.is_approved, t.is_suspended,
                t.certification_level, t.avg_rating, t.total_jobs_completed,
                t.total_jobs_rejected, t.acceptance_rate, t.total_earnings,
                t.service_radius_km,
            ])
            yield buf.getvalue()
            buf.seek(0); buf.truncate(0)

    return StreamingResponse(
        generate(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=technicians.csv"},
    )

